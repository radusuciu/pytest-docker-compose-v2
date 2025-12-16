from contextlib import asynccontextmanager
from typing import Annotated

import psycopg2
import psycopg2.pool as pool
import uvicorn
from fastapi import Depends, FastAPI
from psycopg2.extras import RealDictCursor

db_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname="postgres",
    user="postgres",
    host="my_db",
    port=5432,
)


def get_db_connection():
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)


DbConn = Annotated[psycopg2.extensions.connection, Depends(get_db_connection)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    db_pool.closeall()


app = FastAPI(lifespan=lifespan)


def create_database():
    connection = db_pool.getconn()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS my_table (id serial PRIMARY KEY, num integer, data varchar);"
            )
            connection.commit()
    finally:
        db_pool.putconn(connection)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/all")
def read_all(connection: DbConn):
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM my_table;")
        return [row for row in cursor.fetchall()]


@app.get("/items/{item_id}")
def read_item(item_id: int, connection: DbConn):
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM my_table WHERE num=%s;", (item_id,))
        return cursor.fetchone()


@app.put("/items/{item_id}")
def put_item(item_id: int, connection: DbConn, data_string: str = "abc'def"):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO my_table (num, data) VALUES (%s, %s) " "RETURNING *;",
            (item_id, data_string),
        )
        connection.commit()
        return cursor.fetchone()


@app.delete("/items/{item_id}")
def delete_item(item_id: int, connection: DbConn):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM my_table WHERE num=%s RETURNING *;", (item_id,))
        connection.commit()
        return cursor.fetchone()


if __name__ == "__main__":
    create_database()
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
