from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return """
    <html>
        <body style="
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background-color: #f0f0f0;
            font-family: Arial, sans-serif;
        ">
            <div style="
                text-align: center;
                padding: 50px;
                background-color: white;
                border-radius: 15px;
                box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
            ">
                <img src="https://cdn-icons-png.flaticon.com/512/1995/1995539.png" 
                     width="100px" 
                     alt="heart icon"
                />
                <h1 style="color: #e91e63; font-size: 48px;">
                    Hello Harshi! 🌸, Any one save me?
                </h1>
                <p style="color: #666; font-size: 20px;">
                    Deployed with Kubernetes & Helm
                </p>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
