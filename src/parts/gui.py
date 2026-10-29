def run_web_gui_server():
    from flask import Flask, jsonify, send_from_directory, request, cli as flask_cli
    global api
    ui_dir = Path(GUI_FILE).parent
    assets_dir = ui_dir / "assets"
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    flask_cli.show_server_banner = lambda *args, **kwargs: None

    app = Flask(__name__)
    port = DASHBOARD_PORT
    print(f"[INFO] assets exists: {assets_dir.exists()}")
    api = API()
    app.before_request(lambda: reject_foreign_request(request))

    @app.route('/')
    def index():
        try:
            with open(GUI_FILE, 'r') as f:
                return f.read()
        except:
            return "GUI file not found", 404

    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        assets_path = assets_dir / filename
        if assets_path.exists() and assets_path.is_file():
            resp = send_from_directory(str(assets_dir), filename)
            resp.headers['Cache-Control'] = 'no-store'
            return resp
        print(f"[ERROR] Asset not found: {filename} (looked in {assets_dir})")
        return f"Asset not found: {filename}", 404

    @app.route('/api/console')
    def api_console():
        since = request.args.get('since', 0, type=int)
        with CONSOLE_LOG_LOCK:
            entries = [e for e in CONSOLE_LOG if e["id"] > since]
            latest = CONSOLE_LOG[-1]["id"] if CONSOLE_LOG else since
        return jsonify({"entries": entries, "latest": latest})

    @app.route('/api/profile')
    def api_profile():
        try:
            return jsonify(api.get_user_profile())
        except Exception as e:
            print(f"[ERROR] Error getting profile: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/status')
    def api_status():
        return jsonify({"ready": BOT_READY, "stage": BOOT_STAGE})

    @app.route('/api/rpc', methods=['POST'])
    def api_rpc():
        data = request.get_json(silent=True) or {}
        method_name = str(data.get('method', ''))
        args = data.get('args', [])
        if not isinstance(args, list):
            return jsonify({"error": "args must be a list"}), 400
        method = getattr(api, method_name, None) if not method_name.startswith('_') else None
        if not callable(method):
            return jsonify({"error": f"Unknown method: {method_name}"}), 404
        try:
            return jsonify({"result": method(*args)})
        except Exception as e:
            print(f"[ERROR] RPC {method_name} failed: {e}")
            return jsonify({"error": str(e)}), 500

    # RAILWAY FIX: log the port only (not "localhost"), and bind 0.0.0.0 so the proxy can reach us.
    print(f"[INFO] starting server on port {port}")
    time.sleep(1)
    open_dashboard()
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
