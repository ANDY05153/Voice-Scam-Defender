import os, uuid, warnings
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pydub import AudioSegment
import librosa, numpy as np, joblib

warnings.filterwarnings("ignore")
app = Flask(__name__)
CORS(app)

try:
    classifier = joblib.load("my_voice_defender_model.pkl")
except:
    pass

def extract_features_for_web(file_path):
    try:
        audio, sr = librosa.load(file_path, sr=16000)
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=40)
        return np.hstack((np.mean(mfccs.T, axis=0), np.std(mfccs.T, axis=0)))
    except: return None

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Scam Defender</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%); display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Segoe UI', sans-serif; overflow: hidden; }
        .glass-card { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(12px); border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1); padding: 40px 30px; text-align: center; max-width: 500px; width: 100%; }
        .emoji-icon { font-size: 70px; margin-bottom: 20px; display: inline-block; }
        .main-btn { font-size: 18px; padding: 14px 40px; border-radius: 50px; font-weight: bold; background: linear-gradient(45deg, #0d6efd, #00b4db); border: none; color: white; width: 100%; cursor: pointer; transition: 0.3s;}
        .main-btn:hover { background: linear-gradient(45deg, #00b4db, #0d6efd); transform: scale(1.02); }
        .radar-box { position: relative; width: 80px; height: 80px; margin: 0 auto 20px auto; background: #0d6efd; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; }
        .radar-box::before, .radar-box::after { content: ''; position: absolute; width: 100%; height: 100%; border-radius: 50%; background: rgba(13, 110, 253, 0.4); animation: radar-pulse 2s linear infinite; }
        .radar-box::after { animation-delay: 1s; }
        @keyframes radar-pulse { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(2.5); opacity: 0; } }
        .conf-badge { display: inline-block; padding: 8px 15px; background: rgba(0,0,0,0.05); border-radius: 12px; font-size: 14px; margin-top: 15px; color: #555; text-align: left; line-height: 1.6;}
        .disclaimer { font-size: 12px; color: #888; margin-top: 12px; text-align: left; line-height: 1.5;}
    </style>
</head>
<body>
<div class="container d-flex justify-content-center">
    <div class="glass-card">
        <div id="state-upload">
            <div class="emoji-icon">🛡️</div>
            <h3 class="fw-bold" style="color: #1a237e;">Voice Scam Defender<br><span class="fs-5 text-primary">语音防诈卫士</span></h3>
            <p class="text-muted mt-3 mb-4">Upload a suspicious voice message.<br>上传可疑语音，AI 为您鉴别伪造痕迹。</p>
            <input type="file" id="audioFileInput" accept="audio/*" style="display: none;">
            <button class="main-btn" onclick="document.getElementById('audioFileInput').click();">📁 Select File / 选择文件</button>
            <div id="file-name" class="mt-3 text-primary fw-bold" style="word-break: break-all;"></div>
            <button id="scan-btn" class="main-btn mt-3" style="display: none; background: linear-gradient(45deg, #198754, #20c997);" onclick="startAnalysis()">🔍 Scan Now / 开始本地检测</button>
        </div>
        <div id="state-loading" style="display: none; padding: 20px 0;">
            <div class="radar-box">🤖</div>
            <h4 class="fw-bold text-primary mt-3">Analyzing / 深度声纹分析中...</h4>
        </div>
        <div id="state-safe" style="display: none;">
            <div class="emoji-icon">✅</div>
            <h3 class="text-success fw-bold">SAFE<br><span class="fs-5">未检测到 AI 痕迹</span></h3>
            <div class="alert alert-success border-0 text-start">
                <strong>Analysis Result / 分析结果：</strong><br>No obvious AI synthesis features detected.<br>该音频未呈现明显的 AI 合成声学特征。
                <div class="conf-badge" id="safe-conf"></div>
                <div class="disclaimer">*Notice: Results are for reference only. Do not transfer money easily.<br>*注意：检测结果仅供参考，不代表绝对安全，请勿轻易转账。</div>
            </div>
            <button class="btn btn-outline-secondary w-100 rounded-pill mt-2" onclick="resetApp()">↻ Scan Again / 重新检测</button>
        </div>
        <div id="state-danger" style="display: none;">
            <div class="emoji-icon">🚨</div>
            <h3 class="text-danger fw-bold">SCAM ALERT<br><span class="fs-5">警告：检出 AI 伪造特征</span></h3>
            <div class="alert alert-danger border-0 text-start">
                <strong>Analysis Result / 分析结果：</strong><br>High probability of AI voice cloning. Extreme scam risk!<br>高度疑似 AI 克隆声音，存在极高诈骗风险！
                <div class="conf-badge" id="danger-conf"></div>
                <div class="disclaimer">*Action: Verify identity via video call or call back immediately!<br>*注意：请立刻通过视频通话或挂断重拨核实对方身份！</div>
            </div>
            <button class="btn btn-outline-secondary w-100 rounded-pill mt-2" onclick="resetApp()">↻ Scan Again / 重新检测</button>
        </div>
    </div>
</div>
<script>
    let selectedFile = null;
    document.getElementById('audioFileInput').addEventListener('change', function(e) {
        if(e.target.files.length > 0) {
            selectedFile = e.target.files[0];
            document.getElementById('file-name').innerText = "Selected / 已选择: " + selectedFile.name;
            document.getElementById('scan-btn').style.display = 'block';
        }
    });
    async function startAnalysis() {
        if(!selectedFile) return;
        document.getElementById('state-upload').style.display = 'none';
        document.getElementById('state-loading').style.display = 'block';
        const formData = new FormData(); formData.append("audio", selectedFile);
        try {
            const res = await fetch("/api/analyze", { method: "POST", body: formData });
            const data = await res.json();
            document.getElementById('state-loading').style.display = 'none';
            if (data.status === "success") {
                const confText = "AI Confidence / 模型置信度: <b>" + data.confidence + "</b><br>" + data.engine_info;
                if (data.is_fake) {
                    document.getElementById('state-danger').style.display = 'block';
                    document.getElementById('danger-conf').innerHTML = confText;
                } else {
                    document.getElementById('state-safe').style.display = 'block';
                    document.getElementById('safe-conf').innerHTML = confText;
                }
            } else { alert("Error: " + data.error); resetApp(); }
        } catch (err) { alert("Network Error"); resetApp(); }
    }
    function resetApp() {
        ['state-safe','state-danger','state-loading'].forEach(id => document.getElementById(id).style.display = 'none');
        document.getElementById('state-upload').style.display = 'block';
        document.getElementById('audioFileInput').value = '';
        selectedFile = null; document.getElementById('file-name').innerText = ''; document.getElementById('scan-btn').style.display = 'none';
    }
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/api/analyze', methods=['POST'])
def analyze_audio():
    if 'audio' not in request.files or request.files['audio'].filename == '':
        return jsonify({"error": "No file"}), 400
    
    file = request.files['audio']
    uid = str(uuid.uuid4())
    in_p, out_p = f"temp_{uid}.tmp", f"temp_{uid}.wav"
    
    try:
        file.save(in_p)
        AudioSegment.from_file(in_p).set_channels(1).set_frame_rate(16000).export(out_p, format="wav")
        features = extract_features_for_web(out_p)
        if features is None: return jsonify({"error": "Feature extraction failed"}), 500
            
        pred = classifier.predict([features])[0]
        prob = classifier.predict_proba([features])[0]
        
        return jsonify({
            "status": "success",
            "confidence": f"{prob[pred] * 100:.2f}%",
            "engine_info": "Local Engine / 本地分析引擎 (Random Forest)",
            "is_fake": bool(pred == 1)
        })
    except Exception as e: return jsonify({"error": str(e)}), 500
    finally:
        for p in [in_p, out_p]:
            if os.path.exists(p): os.remove(p)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
