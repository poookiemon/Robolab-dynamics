import os
import sys
import subprocess
import threading
import webbrowser
from flask import Flask, render_template_string, request, jsonify
from auto_runner import AutoRunner

app = Flask(__name__)

execution_logs = []
def add_log(msg):
    execution_logs.append(msg)
    print(msg)

base_dir = os.path.dirname(os.path.abspath(__file__))
biohit_dir = os.path.join(base_dir, "Biohit-Automated-Pipettor-GUI")
analyze_dir = os.path.join(base_dir, "analyze-measurement-py")
contraction_dir = os.path.join(base_dir, "contractiondb-python")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robolab Dynamics</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #fff0f5 0%, #f3e8ff 100%);
            min-height: 100vh;
            color: #333;
        }
        .gradient-text {
            background: linear-gradient(90deg, #ff4d79, #9b4dff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(10px);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.05);
            border: 1px solid rgba(255,255,255,0.5);
        }
        .btn-gradient {
            background: linear-gradient(90deg, #ff4d79, #9b4dff);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-gradient:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(255, 77, 121, 0.3);
        }
        .input-field {
            border: 1px solid #e2e8f0;
            transition: border-color 0.2s;
        }
        .input-field:focus {
            outline: none;
            border-color: #ff4d79;
            box-shadow: 0 0 0 3px rgba(255, 77, 121, 0.1);
        }
        /* Custom scrollbar for logs */
        #logs::-webkit-scrollbar { width: 8px; }
        #logs::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
        #logs::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    </style>
</head>
<body class="p-8 pb-24">

    <!-- Header -->
    <div class="max-w-4xl mx-auto text-center mb-16 mt-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white shadow-lg mb-6">
            <svg class="w-8 h-8 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path></svg>
        </div>
        <h1 class="text-6xl font-extrabold mb-4 tracking-tight gradient-text">Robolab Dynamics</h1>
        <p class="text-xl text-gray-600 font-medium">Unified orchestration and seamless lab automation.</p>
    </div>

    <!-- Main Content -->
    <div class="max-w-4xl mx-auto space-y-8">
        
        <!-- Step 1 -->
        <div class="glass-card rounded-3xl p-8">
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-2xl font-bold"><span class="text-pink-500 mr-2">1.</span> Liquid Handling</h2>
                <button onclick="launch('biohit')" class="px-5 py-2 rounded-xl text-pink-600 font-semibold bg-pink-50 hover:bg-pink-100 transition shadow-sm border border-pink-100 flex items-center">
                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                    Open Biohit Studio
                </button>
            </div>
            <div class="bg-gray-50 rounded-2xl p-5 border border-dashed border-gray-200">
                <label class="block text-sm font-semibold text-gray-500 mb-2">TARGET PROTOCOL (JSON)</label>
                <input type="text" id="path1" placeholder="/path/to/protocol.json" class="input-field w-full px-4 py-3 rounded-xl text-gray-700 bg-white">
            </div>
        </div>

        <!-- Step 2 -->
        <div class="glass-card rounded-3xl p-8">
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-2xl font-bold"><span class="text-purple-500 mr-2">2.</span> Data Analysis</h2>
                <button onclick="launch('analyze')" class="px-5 py-2 rounded-xl text-purple-600 font-semibold bg-purple-50 hover:bg-purple-100 transition shadow-sm border border-purple-100 flex items-center">
                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                    Open Analysis Studio
                </button>
            </div>
            <div class="bg-gray-50 rounded-2xl p-5 border border-dashed border-gray-200">
                <label class="block text-sm font-semibold text-gray-500 mb-2">TARGET FOC DATA FOLDER</label>
                <input type="text" id="path2" placeholder="/path/to/data_folder" class="input-field w-full px-4 py-3 rounded-xl text-gray-700 bg-white">
            </div>
        </div>

        <!-- Step 3 -->
        <div class="glass-card rounded-3xl p-8">
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-2xl font-bold"><span class="text-blue-500 mr-2">3.</span> Database Archiving</h2>
                <button onclick="launch('db')" class="px-5 py-2 rounded-xl text-blue-600 font-semibold bg-blue-50 hover:bg-blue-100 transition shadow-sm border border-blue-100 flex items-center">
                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
                    Open DB Studio
                </button>
            </div>
            <div class="bg-gray-50 rounded-2xl p-5 border border-dashed border-gray-200">
                <label class="block text-sm font-semibold text-gray-500 mb-2">TARGET DB CONFIG (JSON)</label>
                <input type="text" id="path3" placeholder="/path/to/db_config.json" class="input-field w-full px-4 py-3 rounded-xl text-gray-700 bg-white">
            </div>
        </div>

        <!-- Log Area -->
        <div class="glass-card rounded-3xl p-8">
            <h2 class="text-xl font-bold mb-4 text-gray-800">Live Orchestrator Log</h2>
            <div id="logs" class="bg-gray-900 rounded-2xl p-5 h-48 overflow-y-auto font-mono text-sm text-green-400 shadow-inner">
                Waiting for system initialization...
            </div>
        </div>

        <!-- Big Run Button -->
        <button onclick="startRun()" class="btn-gradient w-full py-5 rounded-2xl text-white font-bold text-xl shadow-lg flex justify-center items-center">
            <svg class="w-6 h-6 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
            START AUTOMATED RUN
        </button>

    </div>

    <script>
        function launch(tool) {
            fetch('/api/launch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tool: tool})
            });
        }

        function startRun() {
            const p1 = document.getElementById('path1').value || "auto";
            const p2 = document.getElementById('path2').value || "auto";
            const p3 = document.getElementById('path3').value || "auto";
            
            fetch('/api/start_run', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({protocol: p1, data_dir: p2, db_config: p3})
            });
        }

        setInterval(() => {
            fetch('/api/logs')
                .then(r => r.json())
                .then(data => {
                    const logDiv = document.getElementById('logs');
                    if(data.logs.length > 0) {
                        logDiv.innerHTML = data.logs.map(l => `<div>> ${l}</div>`).join('');
                        logDiv.scrollTop = logDiv.scrollHeight;
                    }
                });
        }, 1000);
    </script>
</body>
</html>
"""

@app.route("/api/launch", methods=["POST"])
def launch():
    data = request.json
    tool = data.get("tool")
    
    if tool == "biohit":
        app_path, cwd = "lims_master_gui.py", biohit_dir
    elif tool == "analyze":
        app_path, cwd = "run_gui.py", analyze_dir
    elif tool == "db":
        app_path, cwd = "examples/contractionDbGui.py", contraction_dir
    else:
        return jsonify({"error": "Invalid tool"}), 400

    target_file = os.path.join(cwd, app_path)
    if not os.path.exists(target_file):
        return jsonify({"error": f"Could not find {app_path}"}), 404

    try:
        cmd = [sys.executable, app_path]
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{cwd}{os.pathsep}{env.get('PYTHONPATH', '')}" if "PYTHONPATH" in env else cwd
        
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        def read_output():
            for line in iter(p.stdout.readline, ''):
                if line: add_log("STUDIO: " + line.strip())
            p.stdout.close()
            add_log(f"--- Studio Closed ({app_path}) ---")
            
        threading.Thread(target=read_output, daemon=True).start()
        add_log(f"--- Launching Studio: {app_path} ---")
        return jsonify({"status": "launched"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/start_run", methods=["POST"])
def start_run():
    data = request.json
    execution_logs.clear()
    add_log("--- Initializing Hands-Free Orchestrator ---")
    runner = AutoRunner(data.get("protocol", ""), data.get("data_dir", ""), data.get("db_config", ""), add_log)
    threading.Thread(target=runner.run_pipeline, daemon=True).start()
    return jsonify({"status": "running"})

@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify({"logs": execution_logs})

if __name__ == "__main__":
    port = 5050
    url = f"http://127.0.0.1:{port}"
    print(f"Server starting on {url}")
    threading.Timer(1.25, lambda: webbrowser.open(url)).start()
    app.run(port=port, debug=False)
