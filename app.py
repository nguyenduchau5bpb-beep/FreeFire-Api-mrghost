from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
import os
from datetime import datetime, timedelta
from Utilities.until import load_accounts
from Api.Account import get_garena_token, get_major_login
from Api.InGame import get_player_personal_show, get_player_stats, search_account_by_keyword

accounts = load_accounts()

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "message": "Free Fire API Server đang hoạt động!",
        "endpoints": [
            "/get_player_personal_show?uid=<UID>&server=VN",
            "/get_player_stats?uid=<UID>&server=VN",
            "/get_search_account_by_keyword?keyword=<NAME>&server=VN"
        ]
    }), 200

@app.route('/get_search_account_by_keyword', methods=['GET'])
def get_search_account_by_keyword():
    try:
        region = request.args.get('server', 'IND').upper()
        search_term = request.args.get('keyword')
        
        if not search_term:
            return json.dumps({"error": "Keyword parameter is required"}, indent=2), 400, {'Content-Type': 'application/json; charset=utf-8'}
        if len(search_term.strip()) < 3:
            return json.dumps({"error": "Keyword must be at least 3 characters long"}, indent=2), 400, {'Content-Type': 'application/json; charset=utf-8'}
        if region not in accounts:
            return json.dumps({"error": f"Invalid server: {region}"}, indent=2), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        auth_response = get_garena_token(accounts[region]['uid'], accounts[region]['password'])
        if not auth_response or 'access_token' not in auth_response:
            return json.dumps({"error": "Authentication failed"}, indent=2), 401, {'Content-Type': 'application/json; charset=utf-8'}
        
        login_response = get_major_login(auth_response["access_token"], auth_response["open_id"])
        if not login_response or 'token' not in login_response:
            return json.dumps({"error": "Major login failed"}, indent=2), 401, {'Content-Type': 'application/json; charset=utf-8'}
        
        search_results = search_account_by_keyword(login_response["serverUrl"], login_response["token"], search_term)
        return json.dumps(search_results, indent=2, ensure_ascii=False), 200, {'Content-Type': 'application/json; charset=utf-8'}
        
    except Exception as e:
        return json.dumps({"error": f"Internal server error: {str(e)}"}, indent=2), 500, {'Content-Type': 'application/json; charset=utf-8'}

@app.route('/get_player_stats', methods=['GET'])
def get_player_stat():
    try:
        server = request.args.get('server', 'IND').upper()
        uid = request.args.get('uid')
        gamemode = request.args.get('gamemode', 'br').lower()
        matchmode = request.args.get('matchmode', 'CAREER').upper()

        if not uid or not uid.isdigit():
            return jsonify({"success": False, "error": "Invalid UID"}), 400
        if server not in accounts:
            return jsonify({"success": False, "error": "Invalid server"}), 400

        garena_token_result = get_garena_token(accounts[server]['uid'], accounts[server]['password'])
        major_login_result = get_major_login(garena_token_result["access_token"], garena_token_result["open_id"])
        
        player_stats = get_player_stats(
            major_login_result["token"], 
            major_login_result["serverUrl"], 
            gamemode, 
            uid, 
            matchmode
        )
        
        if not player_stats:
            return jsonify({"success": False, "error": "No stats data"}), 404

        return jsonify({"success": True, "data": player_stats}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/get_player_personal_show', methods=['GET'])
def get_account_info():
    try:
        server = request.args.get('server', 'IND').upper()
        uid = request.args.get('uid')
        
        if not uid or not uid.isdigit():
            return jsonify({"status": "error", "message": "UID hợp lệ là bắt buộc"}), 400
        
        if server not in accounts:
            return jsonify({"status": "error", "message": f"Server {server} không tồn tại"}), 400

        garena_token_result = get_garena_token(accounts[server]['uid'], accounts[server]['password'])
        major_login_result = get_major_login(garena_token_result["access_token"], garena_token_result["open_id"])
        
        player_personal_show_result = get_player_personal_show(
            major_login_result["serverUrl"], 
            major_login_result["token"], 
            int(uid), 
            False, 7, False, False
        )
        
        if not player_personal_show_result:
            return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu người chơi"}), 404
            
        return json.dumps(player_personal_show_result, indent=2, ensure_ascii=False), 200, {'Content-Type': 'application/json; charset=utf-8'}
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    try:
        from waitress import serve
        port = int(os.environ.get("PORT", 10000))
        print(f"🚀 API Server running on port {port}...")
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        port = int(os.environ.get("PORT", 10000))
        app.run(host='0.0.0.0', port=port)
