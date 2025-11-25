from flask import Flask, render_template, jsonify, request
import scanner

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan')
def api_scan():
    # Get params
    min_mcap = request.args.get('min_mcap', default=0, type=float)
    
    # Trigger scan directly from the master list
    data = scanner.scan_market(min_mcap)
    
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)