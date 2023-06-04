from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from datetime import datetime
import pickle
import pandas as pd
import psycopg2.pool
import os

DATABASE_HOST = os.getenv('DATABASE_HOST')
DATABASE_NAME = os.getenv('DATABASE_NAME')
DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')

conn = psycopg2.connect(
    host=DATABASE_HOST,
    dbname=DATABASE_NAME,
    user=DATABASE_USER,
    password=DATABASE_PASSWORD
)

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000/'])

model = pickle.load(open('model.pkl', 'rb'))

@app.route('/api/v1/predict', methods=["POST"])
@cross_origin()
def predict():
    try:
        user_input = request.json

        date_str = user_input["date"]
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        with conn.cursor() as cur:
            cur.execute("""
                SELECT stops, minutes
                FROM durations
                WHERE source LIKE %s AND destination LIKE %s
                LIMIT 1
            """, ('%' + user_input["source"] + '%', '%' + user_input["destination"] + '%'))
            result = cur.fetchone()

        if result is None:
            final_response = { "status": 400, "message": "Invalid source and destination given." }
            return jsonify(final_response)

        stops, minutes = result


        formatted_user_input = {
            "Airline": user_input["airline"],
            "Source": user_input["source"],
            "Destination": user_input["destination"],
            "Total_Stops": stops,
            "Date": date_obj.day,
            "Month": date_obj.month,
            "Year": date_obj.year,
            "Duration_minutes": minutes
        }

        dataFrames = pd.DataFrame(data=formatted_user_input, index=[0])

        predictions = model.predict(dataFrames)

        with conn.cursor() as cur:
            cur.execute("INSERT INTO graph_data (price, date) VALUES (%s, %s)", (predictions[0], date_obj))
            conn.commit()

        response = {
            "status": 200,
            "predicted_price_in_dollar": predictions[0],
            "predicted_price_in_ngultrum": predictions[0] * 82
        }

        final_response = {**response, **formatted_user_input}
    except ValueError as e:
        final_response = { "status": 400, "message": str(e) }

    return jsonify(final_response)


@app.route('/api/v1/predictions')
@cross_origin()
def predictions():
    cur = conn.cursor()
    cur.execute("""
        SELECT TO_CHAR(DATE_TRUNC('month', date), 'Month') AS month, AVG(price) AS avg_price
        FROM graph_data
        GROUP BY DATE_TRUNC('month', date)
        ORDER BY DATE_TRUNC('month', date) ASC;
    """)

    results = cur.fetchall()
    cur.close()

    avg_prices = []
    for result in results:
        avg_prices.append({
            "month": result[0],
            "price": float(result[1])
        })

    return jsonify(avg_prices)

@app.route('/api/v1/airlines')
@cross_origin()
def airlines():
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT airline
        FROM durations
        ORDER BY airline ASC;
    """)

    airlines = cur.fetchall()

    cur.execute("""
        SELECT DISTINCT source
        FROM durations
        ORDER BY source ASC;
    """)

    sources = cur.fetchall()

    cur.execute("""
        SELECT DISTINCT destination
        FROM durations
        ORDER BY destination ASC;
    """)

    destinations = cur.fetchall()

    cur.close()

    return jsonify({
        "airlines": airlines, 
        "sources": sources,
        "destinations": destinations
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
