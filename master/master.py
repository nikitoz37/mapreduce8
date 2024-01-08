
import json
import os

from flask import (
    Flask,
    #request, 
    #redirect, 
    #url_for, 
    make_response, 
    jsonify
) 
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import insert
import asyncio
import aiohttp


# ----------------------------------------------------------


URL_TXT = 'urls.txt'
SLAVES_COUNT = 2
SLAVES_ADDRESS = (
    'http://172.22.0.1:8001/slave/run',
    'http://172.22.0.1:8002/slave/run',
)
CACHE_SIZE = 1000


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL')
db = SQLAlchemy(app)


class Word(db.Model):
    __tablename__ = 'top_words'

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(30), unique=True, nullable=False)
    num = db.Column(db.Integer, nullable=False)

    def __init__(self, word, num):
        self.word = word
        self.num = num
    
    def json(self):
        return {'id': self.id,'word': self.word, 'email': self.num}


with app.app_context():
    db.create_all()


# ----------------------------------------------------------


def get_urls(file_name: str) -> tuple:
    urls = []
    with open(file_name, 'r', encoding='utf-8') as file:
        for line in file:
            urls.append(line[:-1])
    return tuple(urls)


def data_to_db(data: dict):
    '''new_word = 'город'
    new_num = 5
    
    insert_stmt = insert(Word).values(
        word=new_word,
        num=new_num
    )
    on_update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['word'],
        #constraint = Word.num
        set_=dict(num=Word.num+new_num)
        #set_=dict(num=10)
    )
    db.session.execute(on_update_stmt)
    db.session.commit()'''

    for key, value in data.items():
        insert_stmt = insert(Word).values(
            word=key,
            num=value
        )
        on_update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['word'],
            set_=dict(num=Word.num + value)
        )
        db.session.execute(on_update_stmt)
        db.session.commit()

#def get_top_from_db() -> dict:
    #top_words = Word.query.limit(30).order_by(Word.num).all()
    #jsonify(top_words)
    #return make_response(jsonify([user.json() for user in users]), 200)
    #return top_words


# ----------------------------------------------------------


# Передача url-адресов ведомым
async def get_data(session, slave_addr: str, url: str) -> dict:
    async with session.post(url=slave_addr, json=json.dumps(url, ensure_ascii=False)) as resp:
        words_list = await resp.json(content_type=None)
        return words_list


async def main(work_list) -> list:
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(SLAVES_COUNT):
            #print(work_list[i])
            tasks.append(asyncio.ensure_future(get_data(session, SLAVES_ADDRESS[i], work_list[i])))
        words = await asyncio.gather(*tasks)
        return words

# ----------------------------------------------------------


@app.route('/', methods=['GET'])
def master_info():
    return 'Hello, I am master-container!'
    #return make_response(jsonify({'message': 'test route'}), 200)


'''@app.route('/add', methods=['GET'])
def add():
    return make_response(jsonify({'message': 'test route'}), 200)'''


@app.route('/master/run', methods=['GET'])
def index():
    cache = {}
    work_list = []
    url_tuple = get_urls(URL_TXT)
    for url in url_tuple:
        if (len(work_list) < SLAVES_COUNT):
            work_list.append(url)
        else:
            words = asyncio.run(main(work_list))
            work_list.clear()
            #print(words)

            for page in words:
                for key_page, value_page in page[0].items():
                    if (key_page in cache):
                        cache[key_page] += value_page
                    else:
                        cache[key_page] = value_page

            if (len(cache) > CACHE_SIZE):
                #print('сброс')
                #sorted_cache = dict(sorted(cache.items(), key=lambda item: item[1], reverse=True)) # сортировка значений словаря по убыванию
                data_to_db(cache) # отправка в бд
                cache.clear()
                #break
            else:
                if (key_page in cache):
                    cache[key_page] += value_page
                else:
                    cache[key_page] = value_page

    #top_words = get_top_from_db()
    #return json.dumps(sorted_cache, indent = 4, ensure_ascii=False)
    top_words = Word.query.limit(30).order_by(Word.num).all()               
    return make_response(jsonify([top_words.json() for word in top_words]), 200)
    





