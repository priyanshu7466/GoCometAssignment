"""
Natural language query engine using OpenRouter's free Gemini 2.0 Flash endpoint.
Translates NL questions into SQL, runs against SQLite, and formats the answer.
"""

import json
import sqlite3
import os
from openai import OpenAI
from storage.database import DB_PATH, get_schema

QUERY_PROMPT = """
You are a database query assistant. Given a SQLite database schema and a natural language question, write a valid SQL query to answer the question.

Schema:
{schema}

Question: {question}

CRITICAL RULES:
- Return ONLY valid JSON.
- Do not add markdown blocks outside the JSON.
- Format: {{"sql": "SELECT ...;"}}
- Use the 'shipments' table.
"""

ANSWER_PROMPT = """
You are a helpful assistant. You have been asked a question, a SQL query was run against the database, and the results are provided.
Formulate a clear, concise natural language answer to the user's question based on the results.

Question: {question}
SQL Query: {sql}
Results: {results}

Provide just the natural language answer. No JSON, no markdown.
"""

def ask(question: str) -> dict:
    """
    Answer a natural-language question about shipment data using OpenRouter.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"sql": "-- Error", "answer": "GROQ_API_KEY environment variable not set."}

    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )
    schema = get_schema()

    try:
        # Step 1: Generate SQL
        sql_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": QUERY_PROMPT.format(schema=schema, question=question)}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        content = sql_response.choices[0].message.content
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        sql_dict = json.loads(content.strip())
        sql = sql_dict.get("sql", "").strip()

        # Step 2: Execute SQL
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description] if cursor.description else []
        conn.close()

        formatted_results = [dict(zip(columns, row)) for row in results]

        # Step 3: Generate natural-language answer
        answer_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": ANSWER_PROMPT.format(
                    question=question,
                    sql=sql,
                    results=json.dumps(formatted_results)
                )
            }],
            temperature=0
        )
        
        answer = answer_response.choices[0].message.content.strip()

        return {
            "sql": sql,
            "results": formatted_results,
            "answer": answer
        }

    except Exception as e:
        return {"sql": "Error generating or executing query.", "answer": str(e)}
