from flask import Flask, render_template, request
import argon2
import db_helper 
import logging


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
    results = await db_helper.search_many(query, k=5)
    docs = db_helper.find_best(results, n=5)
    return render_template('documents.html', query=query, password=password, documents=docs)
    # results = {**results, **{k: v for k, v in zip(['aaa', 'bbb', 'ccc'], results.values())}}

    # docs = db_helper.search(query, k=20)
    # docs = db_helper.search_mmr(query, k=20)

    return render_template('results.html', query=query, password=password, results=results)


# if __name__ == '__main__':
#     app.run(debug=True, port=8080)    

