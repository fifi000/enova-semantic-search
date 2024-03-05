import time
import logging

from flask import Flask, render_template, request
import argon2

import db_helper 


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


SECRET_HASH = '$argon2id$v=19$m=65536,t=3,p=4$qWViqDQScp/R+8yBI4X8qg$rMYA0GaZOGpdLo7v/L+Lt5fIWjmwBX/W8ebak69kX+k'


@app.get('/')
@app.get('/search')
def index():
    return render_template('base.html')


@app.post('/search')
async def search():
    password = request.form.get('password') or ''
    query = request.form['q']

    # Check if the password is provided in the request
    try:
        argon2.PasswordHasher().verify(SECRET_HASH, password)
    except:
        return render_template('error.html', error_message='Invalid password', query=query)

    logger.info(f'Query: {query}')
    
    start = time.time()
    docs = await db_helper.asearch(query=query, k=25)
    logger.info(f'Found {len(docs)} documents in {time.time() - start:.4f}s')

    return render_template('documents.html', query=query, password=password, documents=docs)


if __name__ == '__main__':
    app.run(debug=True, port=8080)    

