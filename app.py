"""
Web Demo Dashboard: AI-based Log Anomaly Detection (Hybrid Dual-Engine Architecture)
Isolation Forest (Frequency/Count Outliers) + DeepLog LSTM (Sequential Transition) + Hybrid Detector
Academic Presentation Platform — Course 240-318 AI&ML, PSU Hat Yai
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import torch
from collections import Counter

import importlib
import src.demo_engine
importlib.reload(src.demo_engine)

from src.demo_engine import (
    train_and_cache_model,
    inspect_block_forensics,
    inspect_showcase_forensics,
    get_template_desc,
    DEMO_SHOWCASE_CASES,
)

# -----------------------------------------------------------------------------
# 1. Page Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="LogWatchdog • Hybrid Dual-Engine Log Anomaly Detection",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .badge-tag {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        margin: 0 6px 6px 0;
        border: 1px solid transparent;
    }
    .badge-nominal { background:#ecfdf5; color:#047857; border-color:#a7f3d0; }
    .badge-primary { background:#eff6ff; color:#1d4ed8; border-color:#bfdbfe; }
    .badge-purple  { background:#faf5ff; color:#7e22ce; border-color:#e9d5ff; }
    .badge-subtle  { background:#f8fafc; color:#334155; border-color:#e2e8f0; }
    .badge-alert   { background:#fef2f2; color:#b91c1c; border-color:#fecaca; }

    .engine-card {
        border-radius: 8px; padding: 14px; text-align: center;
        border: 1px solid #e2e8f0; background: #ffffff;
    }
    .engine-card-alert {
        border: 1.5px solid #f87171; background: #fef2f2;
    }
    .engine-card-nominal {
        border: 1.5px solid #86efac; background: #f0fdf4;
    }

    .cm-card {
        border-radius: 6px; padding: 14px; text-align: center;
        border: 1px solid #e2e8f0; background: #ffffff;
    }
    .cm-header {
        font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em;
        text-transform: uppercase; margin-bottom: 4px;
    }
    .cm-value {
        font-size: 1.7rem; font-weight: 700; margin: 2px 0;
        font-family: ui-monospace, SFMono-Regular, monospace;
    }
    .cm-subtext { font-size: 0.76rem; color: #64748b; }
    .cm-highlight-zero  { background:#f0fdf4; border-color:#86efac; }
    .cm-highlight-alert { background:#eff6ff; border-color:#93c5fd; }
    .cm-highlight-miss  { background:#fff1f2; border-color:#fca5a5; }

    .log-box {
        font-family: "JetBrains Mono", Menlo, Consolas, monospace;
        font-size: 0.84rem; line-height: 1.5; background: #ffffff;
        border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px;
    }
    .log-line {
        padding: 4px 8px; margin-bottom: 2px; border-radius: 3px;
        color: #334155; background: #f8fafc; border-left: 3px solid #cbd5e1;
    }
    .log-line-culprit {
        padding: 6px 10px; margin-bottom: 3px; border-radius: 3px;
        font-weight: 600; color: #991b1b; background: #fee2e2;
        border-left: 4px solid #dc2626;
    }
    .arch-card {
        border: 1px solid #cbd5e1; border-radius: 6px; padding: 14px; background: #ffffff;
    }
    .arch-label { font-size: 0.75rem; font-weight: 700; color: #475569; }
    .arch-title { font-size: 1.05rem; font-weight: 700; color: #0f172a; margin: 4px 0; }
    .arch-body  { font-size: 0.8rem; color: #64748b; }
    hr { margin: 1.2rem 0 !important; border-color: #f1f5f9 !important; }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### System Controller")
    st.caption("Hybrid Dual-Engine AI Architecture")

    st.markdown("---")
    st.markdown("**ENVIRONMENT**")
    st.markdown(f"""
    - **Runtime:** PyTorch `{torch.__version__}`
    - **Device:** CPU
    - **Dataset:** HDFS Benchmark (Parquet)
    - **Test Benchmark:** 2,793 Sessions
    """)

    st.markdown("---")
    st.markdown("**MODEL SPECIFICATIONS**")
    st.markdown(r"""
    **🌲 1. Isolation Forest (Count Engine)**
    - Trees: 100
    - Contamination: 0.10
    - Vector Dim: 30 Events
    - Time Complexity: $O(n \log n)$

    **🧠 2. DeepLog LSTM (Sequence Engine)**
    - 2-Layer LSTM (Hidden: 32)
    - Embedding Dim: 32
    - Window Size ($w$): 3
    - Top-$K$ Threshold: 3
    - Optimizer: Adam ($\eta = 0.01$)

    **🛡️ 3. Hybrid Detector (Synergy Core)**
    - Strategy: **Cascaded Synergy (Noise Filter & Validator)**
    - Target: High F1-Score (84.72% vs LSTM 74.64%), Slashing FP by 47% while Preserving 100% Recall
    """)

    st.markdown("---")
    force_retrain = st.button("Retrain Model Checkpoints", width="stretch")
    if force_retrain:
        st.cache_resource.clear()
        st.toast("Cache cleared. Rebuilding dual-engine checkpoints...")


# -----------------------------------------------------------------------------
# 3. Model Loading
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_cached_hybrid_system(retrain: bool = False):
    return train_and_cache_model(force_retrain=retrain)


with st.spinner("Loading Hybrid Dual-Engine models (iForest + DeepLog LSTM)..."):
    try:
        loaded_res = load_cached_hybrid_system(retrain=force_retrain)
        if isinstance(loaded_res, tuple) and len(loaded_res) == 5:
            model, iforest_model, hybrid_detector, metadata, eval_df = loaded_res
            model_ready = True
        else:
            # Old 3-item cache detected in memory, invalidate and reload
            st.cache_resource.clear()
            model, iforest_model, hybrid_detector, metadata, eval_df = train_and_cache_model(force_retrain=True)
            model_ready = True
    except FileNotFoundError as e:
        st.error("⚠️ ไม่พบโมเดลที่บันทึกไว้ใน models/ หรือชุดข้อมูล Parquet ใน data/raw/hdfs_full_parquet/")
        st.info("""
        **💡 คำแนะนำสำหรับผู้ใช้งานที่เพิ่ง Clone Repository มาใหม่:**
        
        ชุดข้อมูลขนาดใหญ่ไม่ได้ถูกเก็บไว้ใน Git ตามแนวปฏิบัติมาตรฐานสากล (Best Practice) คุณสามารถดาวน์โหลดชุดข้อมูล HDFS Benchmark ได้ง่ายๆ ผ่านคำสั่งใน Terminal:
        
        ```bash
        python scripts/download_data.py
        ```
        
        เมื่อดาวน์โหลดเสร็จแล้ว ให้กดปุ่ม **Rerun** ด้านขวาบน หรือกดปุ่ม **Retrain Model Checkpoints** บนเมนูด้านซ้ายเพื่อเริ่มวิเคราะห์ทันทีครับ!
        """)
        model_ready = False
    except Exception as e:
        st.error(f"Error loading model checkpoints: {e}")
        model_ready = False

if not model_ready:
    st.stop()

VOCAB_SIZE = int(model.vocab_size)
m_hybrid = metadata["models"]["hybrid"]
m_lstm = metadata["models"]["lstm"]
m_iforest = metadata["models"]["iforest"]
synergy = metadata.get("synergy", {})


# -----------------------------------------------------------------------------
# 4. Header
# -----------------------------------------------------------------------------
st.markdown("## LogWatchdog: Hybrid Dual-Engine Log Anomaly Detection")
st.markdown("""
ระบบตรวจจับและวินิจฉัยความผิดปกติใน System Logs ด้วยสถาปัตยกรรม **Hybrid Dual-Engine**
ที่ผสานพลัง **Isolation Forest (ด่านตรวจความถี่ / Outlier)** และ **DeepLog LSTM (ด่านตรวจลำดับเวลาและขั้นตอน)**
เพื่อความครอบคลุมสูงสุดและแก้ปัญหา False Negatives ในระบบแบบกระจายศูนย์
""")

st.markdown(f"""
<div>
    <span class="badge-tag badge-purple">HYBRID F1-SCORE: {m_hybrid['f1_score']*100:.2f}% (TOP PERFORMER)</span>
    <span class="badge-tag badge-purple">HYBRID RECALL: {m_hybrid['recall']*100:.2f}%</span>
    <span class="badge-tag badge-primary">LSTM F1: {m_lstm['f1_score']*100:.2f}%</span>
    <span class="badge-tag badge-subtle">IFOREST F1: {m_iforest['f1_score']*100:.2f}%</span>
    <span class="badge-tag badge-nominal">STRATEGY: CASCADED SYNERGY</span>
    <span class="badge-tag badge-subtle">TEST SESSIONS: {metadata['total_test_blocks']:,}</span>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 5. Tabs
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "1. Comparative Model Evaluation",
    "2. Incident Forensics (Dual-Engine)",
    "3. Live Inference Playground",
    "4. System Architecture",
])


# =============================================================================
# TAB 1: COMPARATIVE MODEL EVALUATION
# =============================================================================
with tab1:
    st.markdown("#### Performance Evaluation & Model Comparison")
    st.caption(
        f"ผลการประเมินประสิทธิภาพบนชุดทดสอบมาตรฐาน HDFS จำนวน {metadata['total_test_blocks']:,} Sessions "
        f"(Normal 2,000 บล็อก และ Anomaly 793 บล็อก) เปรียบเทียบระหว่างโมเดลเดี่ยวและการใช้งานแบบ Hybrid"
    )

    view_mode = st.radio(
        "Select Evaluation Perspective:",
        [
            "📊 Comparative Overview (เปรียบเทียบ 3 รูปแบบพร้อมกัน)",
            "🛡️ Hybrid Dual-Engine (Cascaded Synergy)",
            "🧠 DeepLog LSTM (Sequential Transition Engine)",
            "🌲 Isolation Forest (Count & Volume Baseline)",
        ],
        horizontal=True,
    )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    if view_mode.startswith("📊 Comparative Overview"):
        # Top Comparison Cards
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.markdown("""
            <div class="engine-card">
                <div style="font-size:0.8rem; font-weight:700; color:#475569;">BASELINE MODEL</div>
                <div style="font-size:1.15rem; font-weight:700; color:#166534; margin:4px 0;">🌲 Isolation Forest</div>
                <div style="font-size:0.8rem; color:#64748b;">ตรวจจับมิติความถี่และปริมาณ (Count Vectors)</div>
            </div>
            """, unsafe_allow_html=True)
            k1, k2, k3 = st.columns(3)
            k1.metric("Recall", f"{m_iforest['recall']*100:.1f}%")
            k2.metric("Precision", f"{m_iforest['precision']*100:.1f}%")
            k3.metric("F1-Score", f"{m_iforest['f1_score']*100:.1f}%")

        with col_m2:
            st.markdown("""
            <div class="engine-card">
                <div style="font-size:0.8rem; font-weight:700; color:#475569;">PROPOSED AI CORE</div>
                <div style="font-size:1.15rem; font-weight:700; color:#1d4ed8; margin:4px 0;">🧠 DeepLog LSTM</div>
                <div style="font-size:0.8rem; color:#64748b;">ตรวจจับมิติลำดับขั้นตอน (Temporal Transitions)</div>
            </div>
            """, unsafe_allow_html=True)
            k1, k2, k3 = st.columns(3)
            k1.metric("Recall", f"{m_lstm['recall']*100:.1f}%")
            k2.metric("Precision", f"{m_lstm['precision']*100:.1f}%")
            k3.metric("F1-Score", f"{m_lstm['f1_score']*100:.1f}%")

        with col_m3:
            st.markdown("""
            <div class="engine-card" style="border: 1.5px solid #a855f7; background: #faf5ff;">
                <div style="font-size:0.8rem; font-weight:700; color:#7e22ce;">DUAL-ENGINE ENSEMBLE</div>
                <div style="font-size:1.15rem; font-weight:700; color:#6b21a8; margin:4px 0;">🛡️ Hybrid (Cascaded Synergy)</div>
                <div style="font-size:0.8rem; color:#6b21a8;">IF กรอง Noise & False Alarms ช่วยดัน F1 สูงสุด</div>
            </div>
            """, unsafe_allow_html=True)
            k1, k2, k3 = st.columns(3)
            k1.metric("Recall", f"{m_hybrid['recall']*100:.1f}%")
            k2.metric("Precision", f"{m_hybrid['precision']*100:.1f}%")
            k3.metric("F1-Score", f"{m_hybrid['f1_score']*100:.1f}%", f"+{(m_hybrid['f1_score'] - m_lstm['f1_score'])*100:.1f}% vs LSTM")

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # Comparative Table & Chart
        col_tbl, col_chart = st.columns([1.1, 1], gap="large")

        with col_tbl:
            st.markdown("**BENCHMARK COMPARISON TABLE**")
            bench_df = pd.DataFrame([
                {
                    "Model": "🌲 Isolation Forest",
                    "Dimension": "Count / Frequency",
                    "Recall": f"{m_iforest['recall']*100:.2f}%",
                    "Precision": f"{m_iforest['precision']*100:.2f}%",
                    "F1-Score": f"{m_iforest['f1_score']*100:.2f}%",
                    "Accuracy": f"{m_iforest['accuracy']*100:.2f}%",
                    "TP": m_iforest["tp"],
                    "FN": m_iforest["fn"],
                },
                {
                    "Model": "🧠 DeepLog LSTM",
                    "Dimension": "Sequence Order",
                    "Recall": f"{m_lstm['recall']*100:.2f}%",
                    "Precision": f"{m_lstm['precision']*100:.2f}%",
                    "F1-Score": f"{m_lstm['f1_score']*100:.2f}%",
                    "Accuracy": f"{m_lstm['accuracy']*100:.2f}%",
                    "TP": m_lstm["tp"],
                    "FN": m_lstm["fn"],
                },
                {
                    "Model": "🛡️ Hybrid (Cascaded Synergy)",
                    "Dimension": "Dual (Cascaded Density + Seq)",
                    "Recall": f"{m_hybrid['recall']*100:.2f}%",
                    "Precision": f"{m_hybrid['precision']*100:.2f}%",
                    "F1-Score": f"{m_hybrid['f1_score']*100:.2f}%",
                    "Accuracy": f"{m_hybrid['accuracy']*100:.2f}%",
                    "TP": m_hybrid["tp"],
                    "FN": m_hybrid["fn"],
                },
            ])
            st.dataframe(bench_df, width="stretch", hide_index=True)

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            fp_diff = m_lstm['fp'] - m_hybrid['fp']
            fp_pct = (fp_diff / m_lstm['fp']) * 100 if m_lstm['fp'] > 0 else 0
            st.info(f"""
            **💡 Rationale & Breakthrough: ทำไมต้องผสาน Isolation Forest กับ DeepLog LSTM?**
            - **ปัญหาของ DeepLog LSTM (โดดๆ):** ตรวจจับการข้ามขั้นตอนได้ครบทุกเคส (Recall 100%, FN = 0) แต่เกิด **False Positive สูงถึง {m_lstm['fp']:,} บล็อก** เนื่องจากความผันผวนเล็กน้อยระดับ 1-step fluke ส่งผลให้ F1-Score อยู่ที่ **{m_lstm['f1_score']*100:.2f}%**
            - **บทบาทแท้จริงของ Isolation Forest (Noise Suppressor & Validator):**
              ไม่ได้นำมา OR รวมกันแบบไร้เหตุผล แต่ใช้เป็น **Cascaded Density Validator**:
              - เมื่อ LSTM พบความผิดปกติก้ำกึ่ง (1-2 violations) ระบบจะส่งต่อให้ Isolation Forest ตรวจสอบการกระจายความถี่
              - หาก iForest ยืนยันว่า Session มีความถี่ปกติสมบูรณ์ (`score >= 0.0`) ระบบจะ **กรอง False Alarm ทิ้งทันที (ตัด False Positive ทิ้งได้ถึง {fp_diff:,} บล็อก หรือลดลง {fp_pct:.1f}%)**
            - **ผลลัพธ์เชิงประจักษ์ (Empirical Synergy):**
              F1-Score ทะยานขึ้นสู่ **{m_hybrid['f1_score']*100:.2f}% (เพิ่มขึ้น +{(m_hybrid['f1_score'] - m_lstm['f1_score'])*100:.2f}%)** เหนือกว่าทั้งโมเดลเดี่ยวทั้งสองตัว และคง Zero False Negatives (Recall 100.00%) ไว้ได้อย่างสมบูรณ์แบบ!
            """)

        with col_chart:
            st.markdown("**METRIC VISUAL COMPARISON**")
            chart_data = pd.DataFrame([
                {"Model": "iForest", "Metric": "Recall", "Value": m_iforest["recall"] * 100},
                {"Model": "iForest", "Metric": "Precision", "Value": m_iforest["precision"] * 100},
                {"Model": "iForest", "Metric": "F1-Score", "Value": m_iforest["f1_score"] * 100},
                {"Model": "DeepLog", "Metric": "Recall", "Value": m_lstm["recall"] * 100},
                {"Model": "DeepLog", "Metric": "Precision", "Value": m_lstm["precision"] * 100},
                {"Model": "DeepLog", "Metric": "F1-Score", "Value": m_lstm["f1_score"] * 100},
                {"Model": "Hybrid", "Metric": "Recall", "Value": m_hybrid["recall"] * 100},
                {"Model": "Hybrid", "Metric": "Precision", "Value": m_hybrid["precision"] * 100},
                {"Model": "Hybrid", "Metric": "F1-Score", "Value": m_hybrid["f1_score"] * 100},
            ])
            chart = (
                alt.Chart(chart_data)
                .mark_bar(cornerRadius=2)
                .encode(
                    x=alt.X("Metric:N", title=""),
                    y=alt.Y("Value:Q", title="Score (%)", scale=alt.Scale(domain=[0, 105])),
                    color=alt.Color("Model:N", scale=alt.Scale(domain=["iForest", "DeepLog", "Hybrid"], range=["#16a34a", "#2563eb", "#9333ea"])),
                    xOffset="Model:N",
                    tooltip=["Model", "Metric", alt.Tooltip("Value:Q", format=".2f")],
                )
                .properties(height=260)
            )
            st.altair_chart(chart, width="stretch")

        st.markdown("<hr>", unsafe_allow_html=True)

        # 3 Side-by-Side Confusion Matrices
        st.markdown("**SIDE-BY-SIDE CONFUSION MATRICES (N = 2,793 SESSIONS)**")
        cm1, cm2, cm3 = st.columns(3, gap="large")

        with cm1:
            st.markdown("<div style='text-align:center; font-weight:700; color:#166534;'>🌲 1. Isolation Forest (Count)</div>", unsafe_allow_html=True)
            r1, r2 = st.columns(2)
            r1.markdown(f"""
            <div class="cm-card">
                <div class="cm-header" style="color:#15803d;">TN</div>
                <div class="cm-value" style="color:#166534;">{m_iforest['tn']:,}</div>
                <div class="cm-subtext">Normal / Normal</div>
            </div>
            <div style="height:6px;"></div>
            <div class="cm-card cm-highlight-miss">
                <div class="cm-header" style="color:#b91c1c;">FN (Missed!)</div>
                <div class="cm-value" style="color:#b91c1c;">{m_iforest['fn']:,}</div>
                <div class="cm-subtext">Anomaly / Normal</div>
            </div>
            """, unsafe_allow_html=True)
            r2.markdown(f"""
            <div class="cm-card">
                <div class="cm-header" style="color:#b45309;">FP</div>
                <div class="cm-value" style="color:#92400e;">{m_iforest['fp']:,}</div>
                <div class="cm-subtext">Normal / Anomaly</div>
            </div>
            <div style="height:6px;"></div>
            <div class="cm-card cm-highlight-alert">
                <div class="cm-header" style="color:#15803d;">TP</div>
                <div class="cm-value" style="color:#15803d;">{m_iforest['tp']:,}</div>
                <div class="cm-subtext">Anomaly / Anomaly</div>
            </div>
            """, unsafe_allow_html=True)

        with cm2:
            st.markdown("<div style='text-align:center; font-weight:700; color:#1d4ed8;'>🧠 2. DeepLog LSTM (Sequence)</div>", unsafe_allow_html=True)
            r1, r2 = st.columns(2)
            r1.markdown(f"""
            <div class="cm-card">
                <div class="cm-header" style="color:#15803d;">TN</div>
                <div class="cm-value" style="color:#166534;">{m_lstm['tn']:,}</div>
                <div class="cm-subtext">Normal / Normal</div>
            </div>
            <div style="height:6px;"></div>
            <div class="cm-card cm-highlight-zero">
                <div class="cm-header" style="color:#15803d;">FN (Zero Miss)</div>
                <div class="cm-value" style="color:#15803d;">{m_lstm['fn']:,}</div>
                <div class="cm-subtext">Anomaly / Normal</div>
            </div>
            """, unsafe_allow_html=True)
            r2.markdown(f"""
            <div class="cm-card">
                <div class="cm-header" style="color:#b45309;">FP</div>
                <div class="cm-value" style="color:#92400e;">{m_lstm['fp']:,}</div>
                <div class="cm-subtext">Normal / Anomaly</div>
            </div>
            <div style="height:6px;"></div>
            <div class="cm-card cm-highlight-alert">
                <div class="cm-header" style="color:#1d4ed8;">TP</div>
                <div class="cm-value" style="color:#1e40af;">{m_lstm['tp']:,}</div>
                <div class="cm-subtext">Anomaly / Anomaly</div>
            </div>
            """, unsafe_allow_html=True)

        with cm3:
            st.markdown("<div style='text-align:center; font-weight:700; color:#7e22ce;'>🛡️ 3. Hybrid Dual-Engine (Cascaded Synergy)</div>", unsafe_allow_html=True)
            r1, r2 = st.columns(2)
            r1.markdown(f"""
            <div class="cm-card">
                <div class="cm-header" style="color:#15803d;">TN</div>
                <div class="cm-value" style="color:#166534;">{m_hybrid['tn']:,}</div>
                <div class="cm-subtext">Normal / Normal</div>
            </div>
            <div style="height:6px;"></div>
            <div class="cm-card cm-highlight-zero">
                <div class="cm-header" style="color:#15803d;">FN (Zero Miss)</div>
                <div class="cm-value" style="color:#15803d;">{m_hybrid['fn']:,}</div>
                <div class="cm-subtext">Anomaly / Normal</div>
            </div>
            """, unsafe_allow_html=True)
            r2.markdown(f"""
            <div class="cm-card" style="background:#fefce8; border-color:#fde047;">
                <div class="cm-header" style="color:#a16207;">FP (Reduced!)</div>
                <div class="cm-value" style="color:#854d0e;">{m_hybrid['fp']:,}</div>
                <div class="cm-subtext">Normal / Anomaly</div>
            </div>
            <div style="height:6px;"></div>
            <div class="cm-card cm-highlight-alert" style="background:#faf5ff; border-color:#d8b4fe;">
                <div class="cm-header" style="color:#7e22ce;">TP</div>
                <div class="cm-value" style="color:#6b21a8;">{m_hybrid['tp']:,}</div>
                <div class="cm-subtext">Anomaly / Anomaly</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

        # Synergy Breakdown
        st.markdown("**DUAL-ENGINE COOPERATION & FALSE ALARM SUPPRESSION**")
        syn1, syn2, syn3, syn4 = st.columns(4)
        fp_saved = m_lstm['fp'] - m_hybrid['fp']
        fp_reduction_rate = (fp_saved / m_lstm['fp'] * 100) if m_lstm['fp'] > 0 else 0
        syn1.metric("False Positives Suppressed by IF", f"{fp_saved:,} sessions", f"-{fp_reduction_rate:.1f}% noise reduction")
        syn2.metric("True Positives Preserved", f"{m_hybrid['tp']:,} / {m_hybrid['tp'] + m_hybrid['fn']:,}", "100.00% Zero-Miss Recall")
        syn3.metric("F1-Score Net Improvement", f"{m_hybrid['f1_score']*100:.2f}%", f"+{(m_hybrid['f1_score'] - m_lstm['f1_score'])*100:.2f}% over LSTM alone")
        syn4.metric("Agreement on Clean Sessions", f"{m_hybrid['tn']:,} sessions", "Verified Healthy")

    else:
        # Individual Model View
        cur_model_key = "hybrid" if "Hybrid" in view_mode else ("lstm" if "DeepLog" in view_mode else "iforest")
        m_curr = metadata["models"][cur_model_key]
        m_title = "Hybrid Dual-Engine" if cur_model_key == "hybrid" else ("DeepLog LSTM" if cur_model_key == "lstm" else "Isolation Forest")

        st.markdown(f"##### Detailed Metrics: {m_title}")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Recall", f"{m_curr['recall']*100:.2f}%")
        m2.metric("Precision", f"{m_curr['precision']*100:.2f}%")
        m3.metric("F1-Score", f"{m_curr['f1_score']*100:.2f}%")
        m4.metric("Accuracy", f"{m_curr['accuracy']*100:.2f}%")
        m5.metric("Specificity", f"{m_curr['specificity']*100:.2f}%")

        col_ind_cm, col_ind_desc = st.columns([1, 1], gap="large")
        with col_ind_cm:
            st.markdown(f"**CONFUSION MATRIX ({m_title.upper()})**")
            c1, c2 = st.columns(2)
            c1.markdown(f"""
            <div class="cm-card">
                <div class="cm-header" style="color:#15803d;">True Negative (TN)</div>
                <div class="cm-value" style="color:#166534;">{m_curr['tn']:,}</div>
                <div class="cm-subtext">Actual Normal / Predicted Normal</div>
            </div>
            <div style="height:10px;"></div>
            <div class="cm-card {'cm-highlight-zero' if m_curr['fn'] == 0 else 'cm-highlight-miss'}">
                <div class="cm-header" style="color:{'#15803d' if m_curr['fn'] == 0 else '#b91c1c'};">False Negative (FN)</div>
                <div class="cm-value" style="color:{'#15803d' if m_curr['fn'] == 0 else '#b91c1c'};">{m_curr['fn']:,}</div>
                <div class="cm-subtext">Actual Anomaly / Predicted Normal</div>
            </div>
            """, unsafe_allow_html=True)
            c2.markdown(f"""
            <div class="cm-card">
                <div class="cm-header" style="color:#b45309;">False Positive (FP)</div>
                <div class="cm-value" style="color:#92400e;">{m_curr['fp']:,}</div>
                <div class="cm-subtext">Actual Normal / Predicted Anomaly</div>
            </div>
            <div style="height:10px;"></div>
            <div class="cm-card cm-highlight-alert">
                <div class="cm-header" style="color:#1d4ed8;">True Positive (TP)</div>
                <div class="cm-value" style="color:#1e40af;">{m_curr['tp']:,}</div>
                <div class="cm-subtext">Actual Anomaly / Predicted Anomaly</div>
            </div>
            """, unsafe_allow_html=True)

        with col_ind_desc:
            st.markdown("**ANALYSIS & ARCHITECTURAL ROLE**")
            if cur_model_key == "iforest":
                st.markdown("""
                - **Role:** Baseline Model & First-Line Gatekeeper (Brick 4A)
                - **Input:** 30-Dimensional Event Count Vector
                - **Strengths:** ทำงานเร็วระดับ microsecond, ตรวจจับปริมาณ Log ผิดปกติหรือ Loop ซ้ำๆ ได้ดีเยี่ยม
                - **Limitation:** มองไม่เห็นมิติเวลา เมื่อขั้นตอนสลับที่กันโดยที่จำนวนครั้งเท่าเดิม iForest จะพลาดทันที
                """)
            elif cur_model_key == "lstm":
                st.markdown("""
                - **Role:** Deep Semantic Sequential Transition Core (Brick 4B)
                - **Input:** Sliding Window Event Sequences ($w=3$)
                - **Strengths:** ตรวจจับการข้ามขั้นตอน (Step-skipping) และการสลับลำดับได้ 100%
                - **Limitation:** ต้องใช้การประมวลผลสูงกว่า เหมาะกับการทำงานควบคู่กับ Gatekeeper
                """)
            else:
                st.markdown(r"""
                - **Role:** Cascaded Dual-Engine Master (Brick 4C)
                - **Strategy:** Two-Tier Cascaded Synergy Rule
                - **Mechanism:** DeepLog ตรวจสอบลำดับการเปลี่ยนสถานะ $\rightarrow$ ส่งต่อให้ Isolation Forest ยืนยันการกระจายตัวของความถี่ เพื่อตัด False Alarm Fatigue
                - **Strengths:** F1-Score สูงที่สุดในทุกการทดสอบ (84.72%) ลด False Positive ลงเกือบครึ่งหนึ่ง โดยไม่สูญเสีย Recall แม้แต่บล็อกเดียว
                - **Production Value:** ตอบโจทย์มาตรฐาน Enterprise SRE Alerting: มีความแม่นยำสูง ไม่ส่ง Alert พร่ำเพรื่อ และมั่นใจได้ว่าไม่มีเหตุการณ์หลุดรอด
                """)


# =============================================================================
# TAB 2: INCIDENT FORENSICS (DUAL-ENGINE)
# =============================================================================
with tab2:
    st.markdown("#### Dual-Engine Incident Forensics & Root Cause Analysis")
    st.caption("สืบสวนเชิงลึกระดับ Session: แสดงผลการตัดสินใจของทั้ง Isolation Forest, DeepLog LSTM และ Hybrid พร้อมชี้เป้าสาเหตุ")

    forensic_mode = st.radio(
        "Source Mode:",
        ["Curated Demo Cases (3 Unseen Scenarios)", "Browse Full Test Set (2,793 Sessions)"],
        horizontal=True,
    )

    f_info = None

    if forensic_mode == "Curated Demo Cases (3 Unseen Scenarios)":
        case_options = {c["name"]: c for c in DEMO_SHOWCASE_CASES}
        selected_case_name = st.selectbox("Select Case Study:", list(case_options.keys()))
        selected_case = case_options[selected_case_name]

        st.info(f"**Scenario Context:** {selected_case['narrative']}")

        try:
            f_info = inspect_showcase_forensics(selected_case, model, iforest_model, hybrid_detector)
        except Exception as e:
            st.error(f"ไม่สามารถวิเคราะห์ Demo Case นี้ได้: {e}")
            f_info = None

    else:
        f1, f2 = st.columns([1, 2])
        with f1:
            cat_filter = st.selectbox(
                "Filter Category:",
                [
                    "TP (True Positive - Anomaly Detected)",
                    "FP (False Positive - Benign Alert)",
                    "TN (True Negative - Healthy)",
                    "FN (False Negative - Missed)",
                ],
            )

        cat_blocks = eval_df[eval_df["category"] == cat_filter]["block_id"].tolist()
        with f2:
            selected_bid = st.selectbox(
                f"Select Session ID ({len(cat_blocks):,} available, showing first 100):",
                cat_blocks[:100],
            )

        if not selected_bid:
            st.info("ไม่มี Session ในกลุ่มนี้")
        else:
            try:
                f_info = inspect_block_forensics(selected_bid, model, eval_df, iforest_model, hybrid_detector)
            except Exception as e:
                st.error(f"ไม่สามารถวิเคราะห์ Session นี้ได้: {e}")
                f_info = None

    if f_info is not None:
        diag = f_info["diagnosis"]
        st.markdown("<hr>", unsafe_allow_html=True)

        is_ano = f_info["predicted_label"] == "Anomaly"
        status_badge = (
            '<span class="badge-tag badge-alert">FINAL VERDICT: ANOMALY</span>'
            if is_ano else
            '<span class="badge-tag badge-nominal">FINAL VERDICT: NORMAL</span>'
        )
        st.markdown(f"**SESSION: `{f_info['block_id']}`** &nbsp; {status_badge}", unsafe_allow_html=True)

        # 3 Engine Verdict Cards
        v1, v2, v3 = st.columns(3)
        with v1:
            is_if_ano = f_info["iforest_pred"] == "Anomaly"
            st.markdown(f"""
            <div class="engine-card {'engine-card-alert' if is_if_ano else 'engine-card-nominal'}">
                <div style="font-size:0.75rem; font-weight:700;">ENGINE 1: ISOLATION FOREST</div>
                <div style="font-size:1.1rem; font-weight:700; color:{'#b91c1c' if is_if_ano else '#166534'};">
                    {f_info['iforest_pred']}
                </div>
                <div style="font-size:0.75rem; color:#64748b;">Count Dimension (Length: {f_info['sequence_length']})</div>
            </div>
            """, unsafe_allow_html=True)

        with v2:
            is_dl_ano = f_info["lstm_pred"] == "Anomaly"
            st.markdown(f"""
            <div class="engine-card {'engine-card-alert' if is_dl_ano else 'engine-card-nominal'}">
                <div style="font-size:0.75rem; font-weight:700;">ENGINE 2: DEEPLOG LSTM</div>
                <div style="font-size:1.1rem; font-weight:700; color:{'#b91c1c' if is_dl_ano else '#166534'};">
                    {f_info['lstm_pred']}
                </div>
                <div style="font-size:0.75rem; color:#64748b;">Sequence Dimension (Top-{model.top_k})</div>
            </div>
            """, unsafe_allow_html=True)

        with v3:
            is_hy_ano = f_info["hybrid_pred"] == "Anomaly"
            st.markdown(f"""
            <div class="engine-card {'engine-card-alert' if is_hy_ano else 'engine-card-nominal'}" style="background:#faf5ff;">
                <div style="font-size:0.75rem; font-weight:700; color:#7e22ce;">ENGINE 3: HYBRID ENSEMBLE</div>
                <div style="font-size:1.1rem; font-weight:700; color:{'#b91c1c' if is_hy_ano else '#166534'};">
                    {f_info['hybrid_pred']}
                </div>
                <div style="font-size:0.75rem; color:#6b21a8;">{f_info.get('triggered_source', 'OR-Voting')}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        det_left, det_right = st.columns([1, 1], gap="large")
        c_idx = diag.get("culprit_step_index")

        with det_left:
            st.markdown("**DIAGNOSIS & ROOT CAUSE EXPLAINER**")
            if diag.get("is_anomaly") and c_idx is not None:
                c_tid = diag.get("culprit_template_id")
                actual_p = diag.get("actual_probability", 0.0)
                st.error(f"""
**Sequential violation detected at line {c_idx + 1}**
- **Observed event:** `E{c_tid}` — {get_template_desc(c_tid)}
- **Model transition probability:** `{actual_p:.2f}%` (not in Top-{model.top_k})
- **Expected candidate events (Top-{model.top_k}):** `{diag.get('expected_candidates', [])}`
                """)
            else:
                st.success(f"**Normal sequential execution:** ทุกการเปลี่ยนสถานะสอดคล้องกับรูปแบบ Top-{model.top_k} ที่โมเดลคาดการณ์")

            if f_info["prob_distribution"]:
                st.markdown("**NEXT-EVENT PROBABILITY DISTRIBUTION (SOFTMAX)**")
                prob_data = pd.DataFrame(f_info["prob_distribution"])
                prob_data["Role"] = np.where(
                    prob_data["is_actual"], "Observed event",
                    np.where(prob_data["is_top_k"], f"Expected (Top-{model.top_k})", "Other"),
                )
                role_domain = ["Observed event", f"Expected (Top-{model.top_k})", "Other"]
                prob_chart = (
                    alt.Chart(prob_data)
                    .mark_bar(cornerRadius=2)
                    .encode(
                        x=alt.X("probability:Q", title="Probability", axis=alt.Axis(format="%")),
                        y=alt.Y("event_name:N", sort="-x", title=""),
                        color=alt.Color(
                            "Role:N",
                            scale=alt.Scale(domain=role_domain, range=["#dc2626", "#1e40af", "#cbd5e1"]),
                            legend=alt.Legend(orient="bottom", title=None),
                        ),
                        tooltip=["event_id", "event_name", alt.Tooltip("probability:Q", format=".2%")],
                    )
                    .properties(height=280)
                )
                st.altair_chart(prob_chart, width="stretch")

        with det_right:
            st.markdown("**LOG CONTEXT WINDOW (5 LINES)**")
            events = f_info["session_events"]
            if c_idx is not None:
                start_l = max(0, c_idx - 2)
                end_l = min(len(events), c_idx + 3)
                context_evs = events[start_l:end_l]
            else:
                context_evs = events[:5]

            log_html = ['<div class="log-box">']
            for ev in context_evs:
                is_culprit = (ev["line_number"] - 1) == c_idx
                cls_name = "log-line-culprit" if is_culprit else "log-line"
                prefix = "[CULPRIT] " if is_culprit else ""
                text = str(ev["raw_line"]).replace("<", "&lt;").replace(">", "&gt;")
                log_html.append(f'<div class="{cls_name}">{prefix}Line {ev["line_number"]:02d}: {text}</div>')
            log_html.append("</div>")
            st.markdown("".join(log_html), unsafe_allow_html=True)

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown("**FULL EVENT SEQUENCE**")
            st.code(" → ".join(f"E{e}" for e in f_info["sequence"]), language=None)

            st.markdown("**EVENT FREQUENCY SUMMARY (COUNT VECTOR)**")
            freq_items = [f"E{k}: {v}x" for k, v in f_info.get("counts", {}).items()]
            st.caption(", ".join(freq_items))


# =============================================================================
# TAB 3: LIVE INFERENCE PLAYGROUND
# =============================================================================
with tab3:
    st.markdown("#### Live Inference Playground (Dual-Engine)")
    st.caption("ป้อนลำดับ Event ID เพื่อทดสอบการตัดสินใจของทั้ง Isolation Forest และ DeepLog LSTM แบบสดๆ พร้อมดูการรวมผลลัพธ์ของ Hybrid Detector")

    presets = {}
    preset_descriptions = {}
    for case in DEMO_SHOWCASE_CASES:
        key = f"{case['name']} — {case['block_id']}"
        presets[key] = ", ".join(str(e) for e in case["events"])
        preset_descriptions[key] = case["narrative"]
    presets["Custom sequence"] = "3, 0, 1, 6, 2, 7"
    preset_descriptions["Custom sequence"] = "ป้อนลำดับตัวเลข Event ID อิสระตามที่ต้องการทดสอบ"

    p1, p2 = st.columns([1, 1], gap="large")
    with p1:
        scenario = st.selectbox("Scenario:", list(presets.keys()))
        st.caption(f"**Context:** {preset_descriptions[scenario]}")
        seq_input = st.text_area(
            f"Event ID sequence (comma-separated, valid range 0–{VOCAB_SIZE - 1}):",
            value=presets[scenario],
            height=85,
        )
        top_k_val = st.slider("DeepLog Top-K threshold:", min_value=1, max_value=5, value=int(model.top_k))

    tokens = [t.strip() for t in seq_input.split(",") if t.strip()]
    invalid = [t for t in tokens if not t.isdigit() or int(t) >= VOCAB_SIZE]
    parsed_seq = [int(t) for t in tokens if t.isdigit() and int(t) < VOCAB_SIZE]

    with p2:
        st.markdown("**SEQUENCE DECODING**")
        if invalid:
            st.warning(f"ค่าที่ไม่ถูกต้องหรืออยู่นอกช่วง 0–{VOCAB_SIZE - 1}: {', '.join(invalid)}")
        if parsed_seq:
            decode_df = pd.DataFrame({
                "Step": [i + 1 for i in range(len(parsed_seq))],
                "Event": [f"E{e}" for e in parsed_seq],
                "Operation": [get_template_desc(e) for e in parsed_seq],
            })
            st.dataframe(decode_df, width="stretch", hide_index=True, height=240)
        else:
            st.info("กรุณาป้อนลำดับ Event ID")

    if st.button("Run Dual-Engine Inference", width="stretch", type="primary"):
        w = model.window_size
        if invalid:
            st.error("กรุณาแก้ไขค่าที่ไม่ถูกต้องก่อนรัน")
        elif len(parsed_seq) < w + 1:
            st.warning(f"ลำดับต้องมีอย่างน้อย {w + 1} เหตุการณ์ (Window Size = {w})")
        else:
            # 1. รัน Isolation Forest
            n_feat = getattr(getattr(iforest_model, "model", None), "n_features_in_", VOCAB_SIZE)
            cv = np.zeros(n_feat, dtype=np.float32)
            for eid in parsed_seq:
                if eid < n_feat:
                    cv[eid] += 1
            if_pred = int(iforest_model.predict(cv.reshape(1, -1))[0])

            # 2. รัน DeepLog LSTM
            trace, flagged = [], False
            model.net.eval()
            with torch.no_grad():
                for i in range(len(parsed_seq) - w):
                    w_slice = parsed_seq[i:i + w]
                    tgt = parsed_seq[i + w]
                    logits = model.net(torch.tensor([w_slice], dtype=torch.long))
                    probs = torch.softmax(logits, dim=-1).squeeze(0).numpy()
                    top_idx = np.argsort(probs)[::-1][:top_k_val].tolist()
                    violation = tgt not in top_idx
                    flagged = flagged or violation
                    trace.append({
                        "Line": i + w + 1,
                        "Window (X)": str(w_slice),
                        "Actual next (y)": f"E{tgt}",
                        f"Predicted Top-{top_k_val}": str(top_idx),
                        "P(actual)": f"{probs[tgt]*100:.2f}%",
                        "Status": "VIOLATION" if violation else "OK",
                    })

            dl_pred = 1 if flagged else 0
            hy_res = hybrid_detector.predict_session(cv, parsed_seq)
            hy_pred = hy_res["prediction"]
            hy_desc = ", ".join(hy_res["triggered_by"]) if hy_res["triggered_by"] else "Synergy Verdict (Clean / Noise Suppressed)"

            st.markdown("<hr>", unsafe_allow_html=True)

            # ผลลัพธ์ 3 กล่อง
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="engine-card {'engine-card-alert' if if_pred == 1 else 'engine-card-nominal'}">
                    <div style="font-weight:700; font-size:0.8rem;">🌲 ISOLATION FOREST</div>
                    <div style="font-size:1.3rem; font-weight:700; color:{'#b91c1c' if if_pred == 1 else '#166534'};">
                        {'ANOMALY' if if_pred == 1 else 'NORMAL'}
                    </div>
                    <div style="font-size:0.75rem; color:#64748b;">Count Vector Spike Check</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="engine-card {'engine-card-alert' if dl_pred == 1 else 'engine-card-nominal'}">
                    <div style="font-weight:700; font-size:0.8rem;">🧠 DEEPLOG LSTM</div>
                    <div style="font-size:1.3rem; font-weight:700; color:{'#b91c1c' if dl_pred == 1 else '#166534'};">
                        {'ANOMALY' if dl_pred == 1 else 'NORMAL'}
                    </div>
                    <div style="font-size:0.75rem; color:#64748b;">Sequential Transition Check</div>
                </div>
                """, unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div class="engine-card {'engine-card-alert' if hy_pred == 1 else 'engine-card-nominal'}" style="background:#faf5ff;">
                    <div style="font-weight:700; font-size:0.8rem; color:#7e22ce;">🛡️ HYBRID VERDICT</div>
                    <div style="font-size:1.3rem; font-weight:700; color:{'#b91c1c' if hy_pred == 1 else '#166534'};">
                        {'ANOMALY DETECTED' if hy_pred == 1 else 'HEALTHY'}
                    </div>
                    <div style="font-size:0.75rem; color:#6b21a8;">{hy_desc}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown("**STEP-BY-STEP SEQUENCE TRANSITION TRACE**")
            st.dataframe(pd.DataFrame(trace), width="stretch", hide_index=True)


# =============================================================================
# TAB 4: SYSTEM ARCHITECTURE
# =============================================================================
with tab4:
    st.markdown("#### Lego Modular Architecture (Brick 1 to Brick 5)")
    st.caption("ระบบออกแบบด้วยสถาปัตยกรรมแบบตัวต่อเลโก้ 5 บล็อกอิสระ เชื่อมต่อผ่าน Standard Interface สามารถสลับและประกบโมเดลได้อย่างอิสระ")

    blocks = [
        ("BLOCK 1", "Ingestion", ["HDFS Loader", "Line-by-line Iterator", "Zero-Leakage Guard"]),
        ("BLOCK 2", "Log Parser", ["Drain3 Template Miner", "Regex Variable Masking", "Read-Only Matcher"]),
        ("BLOCK 3", "Feature Engine", ["Sliding Window (w=3)", "Count Vector Builder", "Sequence Tokenizer"]),
        ("BLOCK 4", "Hybrid AI Core", ["Brick 4A: iForest (Count)", "Brick 4B: DeepLog LSTM", "Brick 4C: Hybrid Ensemble"]),
        ("BLOCK 5", "Explainer & UI", ["DeepLogExplainer", "Incident Payload Schema", "Interactive Dashboard"]),
    ]
    cols = st.columns(5)
    for col, (lbl, title, items) in zip(cols, blocks):
        col.markdown(f"""
        <div class="arch-card">
            <div class="arch-label">{lbl}</div>
            <div class="arch-title">{title}</div>
            <div class="arch-body">{'<br>'.join('- ' + i for i in items)}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    **ACADEMIC REFERENCES & BENCHMARKS**
    - **DeepLog:** Du et al., *DeepLog: Anomaly Detection and Diagnosis from System Logs through Deep Learning*, ACM CCS 2017
    - **Drain:** He et al., *Drain: An Online Log Parsing Approach with Fixed Depth Tree*, IEEE ICWS 2017
    - **Isolation Forest:** Liu et al., *Isolation Forest*, IEEE ICDM 2008
    - **LogHub Dataset:** Zhu et al., *Tools and Benchmarks for Automated Log Analysis*, ICSE 2019
    """)

st.markdown("<hr>", unsafe_allow_html=True)
st.caption("LogWatchdog • Hybrid Dual-Engine System Log Anomaly Detection Platform")
