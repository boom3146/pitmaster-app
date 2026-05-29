import streamlit as st
import time
import uuid
import pandas as pd
import os
import requests

# --- הגדרות דף ---
st.set_page_config(page_title="Pitmaster Pro Ultimate", page_icon="🥩", layout="wide")

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzFbREv3LpOI1rMCGKIsy6hCH9ywMsq4bKalT-XeaZveMuKCHkLmUw7z5zjPz236yEE/exec"

# --- 1. הזרקת עיצוב (CSS) מרוכז ונקי ---
st.markdown("""
<style>
/* 1. הגדרות רקע וטקסט כללי */
.stApp { background-color: #0e1117; }
.stApp p, .stApp label, .stMarkdown p, .stText, .stMarkdown li, .stMarkdown span { color: #ffffff !important; }

/* 2. יישור לימין (RTL) מושלם */
.stMarkdown, .stCaption { text-align: right !important; direction: rtl !important; }
.stMarkdown ul, .stMarkdown ol { direction: rtl !important; padding-right: 2.5rem !important; }

/* --- 3. הפתרון המוחלט לגבולות (עובד בכל דפדפן) --- */

/* א. נותן מסגרת עבה לכל הריבועים (זה יתפוס ויעבה את אזור "סוג הנתח") */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 3px solid #777777 !important;
    border-radius: 12px !important;
}

/* ב. נותן מסגרת עבה לריבוע של המנגל עצמו (הקונטיינר עם הגובה) */
div[data-testid="stScrollableContainer"] {
    border: 3px solid #777777 !important;
    border-radius: 12px !important;
}

/* ג. מחזיר לגבול דק ועדין *רק* את הנתחים שבתוך המנגל, כדי שלא יהיו גסים מדי */
div[data-testid="stScrollableContainer"] div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #444444 !important;
    border-radius: 8px !important;
}
/* ------------------------------------------------ */

/* 4. עיצוב תפריטים נפתחים (Expanders) */
[data-testid="stExpander"] {
    margin-top: 0px !important;
    margin-bottom: 15px !important;
    border: 2px solid #555555 !important;
    border-radius: 10px !important;
    background-color: #1a1a1a !important;
}
[data-testid="stExpander"] details summary {
    padding: 12px 18px !important; 
    background-color: #1a1a1a !important; 
    color: #ff4b4b !important;
}
[data-testid="stExpanderDetails"] { background-color: #1a1a1a !important; }

/* 5. עיצוב כפתורים */
div.stButton > button {
    background-color: #2b2b2b !important;
    border: 1px solid #777 !important;
    border-radius: 8px !important;
    width: 100%;
    color: white !important;
    transition: 0.3s;
}
div.stButton > button:hover { border-color: #ff4b4b !important; color: #ff4b4b !important; background-color: #0e1117 !important; }
h1, h2, h3 { color: #ff4b4b !important; text-align: right; }
.stProgress > div > div > div > div { background-color: #ff4b4b; }
.empty-grill-box, .empty-grill-box h3, .empty-grill-box p { text-align: center !important; color: #666 !important; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- אתחול משתני מצב ---
if 'grill_items' not in st.session_state:
    st.session_state.grill_items = {}
if 'history_log' not in st.session_state:
    st.session_state.history_log = []


# --- פונקציות עזר לצלילים ---
def play_flip_sound():
    st.markdown(
        '<audio autoplay><source src="https://www.soundjay.com/buttons/sounds/button-09.mp3" type="audio/mpeg"></audio>',
        unsafe_allow_html=True)


def play_done_sound():
    st.markdown(
        '<audio autoplay><source src="https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3" type="audio/mpeg"></audio>',
        unsafe_allow_html=True)


# --- נתונים מקצועיים ---
MEAT_DATA = {
    "אנטריקוט": {"base": 100, "safe_temp": False, "rest_factor": 2.5, "fixed_thick": None, "heat_zone": "ישיר (חזק) ואז עקיף", "salt": "מלח גס בנדיבות. 'Dry Brine' של 40 דקות לפחות."},
    "סינטה": {"base": 90, "safe_temp": False, "rest_factor": 2.0, "fixed_thick": None, "heat_zone": "ישיר (חזק)", "salt": "המלחה מראש מומלצת. חצי כפית לכל צד."},
    "פילה": {"base": 85, "safe_temp": False, "rest_factor": 2.5, "fixed_thick": None, "heat_zone": "ישיר (בינוני-חזק)", "salt": "מלח גס איטלקי רגע לפני האש."},
    "דנוור": {"base": 95, "safe_temp": False, "rest_factor": 2.0, "fixed_thick": None, "heat_zone": "ישיר (חזק)", "salt": "Dry Brining של 40 דקות עוזר לריכוך."},
    "פיקניה": {"base": 110, "safe_temp": False, "rest_factor": 2.5, "fixed_thick": None, "heat_zone": "עקיף ואז צריבה ישירה בשומן", "salt": "המלחה גסה על שכבת השומן."},
    "נתח קצבים": {"base": 80, "safe_temp": False, "rest_factor": 2.0, "fixed_thick": None, "heat_zone": "ישיר (חזק מאוד)", "salt": "מלח גס רגע לפני (צריבה מהירה)."},
    "צלעות": {"base": 120, "safe_temp": False, "rest_factor": 3.0, "fixed_thick": 2.5, "heat_zone": "ישיר (בינוני)", "salt": "חלק מהראב (תיבול יבש) לפני הצלייה."},
    "המבורגר": {"base": 100, "safe_temp": True, "rest_factor": 0, "fixed_thick": 2.0, "heat_zone": "ישיר (חזק)", "salt": "המלחה מבחוץ רגע לפני."},
    "קבב": {"base": 120, "safe_temp": True, "rest_factor": 0, "fixed_thick": 2.5, "heat_zone": "ישיר (בינוני)", "salt": "המלח בתערובת. אין להוסיף מבחוץ."},
    "לבבות": {"base": 150, "safe_temp": True, "rest_factor": 0, "fixed_thick": 1.0, "heat_zone": "ישיר (בינוני)", "salt": "המלחה עדינה במרינדה."},
    "חזה עוף": {"base": 140, "safe_temp": True, "rest_factor": 0.5, "fixed_thick": 1.5, "heat_zone": "ישיר (בינוני)", "salt": "המלחה עדינה במרינדה."},
    "פרגית": {"base": 160, "safe_temp": True, "rest_factor": 0.5, "fixed_thick": 1.0, "heat_zone": "ישיר (בינוני-חזק)", "salt": "בתוך המרינדה."},
    "חזה מולארד": {"base": 130, "safe_temp": False, "rest_factor": 2.0, "fixed_thick": None, "heat_zone": "ישיר (חזק) בצד השומן", "salt": "חריצת שומן והמלחה."},
    "כבד אווז": {"base": 40, "safe_temp": False, "rest_factor": 0, "fixed_thick": 1.5, "heat_zone": "ישיר (חזק מאוד)", "salt": "צריבה מהירה."},
    "נקניקיות": {"base": 60, "safe_temp": True, "rest_factor": 0, "fixed_thick": 2.0, "heat_zone": "ישיר (בינוני)", "salt": "אין צורך במלח."},
    "צוריסוס": {"base": 150, "safe_temp": True, "rest_factor": 0, "fixed_thick": 2.5, "heat_zone": "ישיר (בינוני-חלש)", "salt": "אין צורך במלח."},
    "מרגז": {"base": 140, "safe_temp": True, "rest_factor": 0, "fixed_thick": 1.5, "heat_zone": "ישיר (בינוני)", "salt": "אין צורך במלח."}
}

st.title("🥩 Pitmaster Pro Ultimate")

# --- חלוקה לעמודות ראשיות ---
col_control, col_fire = st.columns([1, 1.2], gap="large")

with col_control:
    st.subheader("🛠️ הכנות ובקרה")

    # צ'קליסט חומרה
    with st.expander("🛠️ צ'קליסט ציוד (Hardware Check)"):
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            st.checkbox("כלי מנגל (מלקחיים, מזלג, מברשת)")
            st.checkbox("קרש חיתוך")
            st.checkbox("בצל חתוך בקערה עם שמן")
        with c_p2:
            st.checkbox("סכין פריסה חדה")
            st.checkbox("שמן")
            st.checkbox("נייר סופג")
        with c_p3:
            st.checkbox("פחמים")
            st.checkbox("מגשי אלומיניום")
            st.checkbox("גפרורים")

    # מחשבון כמויות
    with st.expander("📅 תכנון כמויות למסיבה (Party Planner)"):
        c_men = st.number_input("גברים:", 0, 100, 0)
        c_women = st.number_input("נשים:", 0, 100, 0)
        c_kids = st.number_input("ילדים:", 0, 100, 0)
        st.info(f"💡 כמות מומלצת לקנייה: **{(c_men * 0.4 + c_women * 0.3 + c_kids * 0.2):.2f} ק''ג**")

    # הוספת נתח למנגל
    with st.container(border=True):
        meat = st.selectbox("סוג הנתח:", list(MEAT_DATA.keys()))
        st.info(f"🧂 **הכנה:** {MEAT_DATA[meat]['salt']} | 🔥 **אש:** {MEAT_DATA[meat]['heat_zone']}")
        is_poultry = MEAT_DATA[meat]["safe_temp"]

        if MEAT_DATA[meat]["fixed_thick"]:
            thick = MEAT_DATA[meat]["fixed_thick"]
            st.info(f"📏 עובי סטנדרטי: {thick} ס''מ")
        else:
            thick = st.number_input("עובי (ס''מ):", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

        if is_poultry:
            done = "Well Done"
            mult_val = 1.0
            st.warning("🔥 נתח זה דורש צלייה מלאה")
        else:
            done = st.select_slider("מידת עשייה:", ["Rare", "Medium-Rare", "Medium", "Medium-Well", "Well Done"],
                                    "Medium")
            mult_val = {"Rare": 0.6, "Medium-Rare": 0.8, "Medium": 1.0, "Medium-Well": 1.2, "Well Done": 1.5}[done]

        if st.button("📥 הוסף למנגל"):
            new_id = str(uuid.uuid4())
            st.session_state.grill_items[new_id] = {
                "id": new_id, "name": meat, "done_level": done, "thickness": thick,
                "side_time": int(thick * MEAT_DATA[meat]['base'] * mult_val),
                "rest_time": int(thick * MEAT_DATA[meat]['rest_factor'] * 60),
                "phase": "waiting", "end_time": 0, "done_time": None
            }

    # מרינדות
        with st.expander("🍯 ספריית מרינדות ותבלינים (כשר 💯)"):
            st.markdown("""
            ### 🥩 נתחי בקר (סינטה, דנוור, צלעות)
            * **הקלאסית:** שמן זית, חומץ בלסמי, שום כתוש, מעט חרדל דיז'ון, דבש ופלפל שחור.
              * ⏳ **זמן השריה:** 2-4 שעות במקרר (החומץ יתחיל לפרק את הבשר אם יישאר יותר מזה).
            * **צ'ימיצ'ורי ירוק (כמרינדה או רוטב):** המון פטרוזיליה וכוסברה, שיני שום, שמן זית, חומץ בן יין אדום, אורגנו יבש וצ'ילי גרוס.
              * ⏳ **זמן השריה:** שעתיים-שלוש כמרינדה מראש, או להגיש כרוטב טרי ולמרוח על הנתח מיד כשירד מהאש.
            * **ראב טקסס (יבש - לצלעות):** סוכר חום, פפריקה מעושנת, אבקת שום, אבקת בצל, פלפל שחור גרוס קשה, ומעט אבקת חרדל.
              * ⏳ **זמן מריחה:** לפחות שעתיים לפני, מומלץ לעסות את הבשר 12-24 שעות מראש ולהשאיר במקרר ללא כיסוי לקראסט מושלם.
            * **ראב קפה שחור (למתקדמים):** קפה שחור טחון (מרירות שמוסיפה המון עומק), סוכר חום כהה, פלפל שחור ופפריקה חריפה.
              * ⏳ **זמן מריחה:** 1-4 שעות לפני הצלייה.

            ### 🍗 עוף (פרגית, חזה עוף, לבבות)
            * **ים תיכוני קלאסי:** שמן זית, פפריקה מעושנת, כמון, כורכום, מיץ לימון טרי והמון בצל חי מגורד.
              * ⏳ **זמן השריה:** שעתיים לפחות, אידיאלי להשרות למשך לילה שלם (עד 12 שעות). מיץ הבצל מרכך את העוף בצורה פנומנלית.
            * **אסייתי מתוק-מלוח:** רוטב סויה, מעט שמן שומשום, סילאן, ג'ינג'ר טרי מגורד ושום.
              * ⏳ **זמן השריה:** 1-4 שעות. ללבבות (שהם נתח קטן) מספיקה גם חצי שעה-שעה.
            * **מקסיקני אש:** שמן זית, מיץ מליים/לימון, פפריקה חריפה/צ'יפוטלה, כמון, כוסברה טרייה קצוצה דק ושבבי צ'ילי.
              * ⏳ **זמן השריה קריטי:** 2-3 שעות גג! חומציות הליים תכבוש את העוף ותהרוס לו את המרקם אם יישאר שם לילה שלם.

            ### 🦆 מיוחדים (חזה מולארד)
            * **תפוז-ג'ינג'ר:** מיץ תפוזים טרי, כוכב אניס אחד, רוטב סויה, שום, ומעט סילאן. חמיצות התפוז שוברת את השומניות.
              * ⏳ **זמן השריה:** 2-6 שעות במקרר.

            💡 **כלל ברזל לפיטמאסטר:** נתחי פרימיום כמו אנטריקוט, פילה, פיקניה וכבד אווז – **לא מקבלים מרינדה!** מלח גס, פלפל שחור גרוס רגע לפני (או אחרי) האש, תנו לאיכות של הבשר לדבר.
            """)

with col_fire:
    st.subheader("🔥 המנגל בפעולה")

    # פתרון הקסם: שימוש בקונטיינר מובנה של Streamlit עם גובה קבוע!
    # הוא דואג בעצמו להישאר בגובה 600 ולשמור את הכל בפנים.
    with st.container(height=655):
        st.markdown('<div class="marker-right-box"></div>', unsafe_allow_html=True)
        @st.fragment(run_every=1)
        def render_grill():
            if not st.session_state.grill_items:
                # שימוש בקלאס המיוחד שמרכז בכוח
                st.markdown("""
                                <div class='empty-grill-box' style='margin-top: 200px;'>
                                    <h3>🥩 המנגל ריק...<br>מחכה לנתחים שלך</h3>
                                </div>
                            """, unsafe_allow_html=True)
            else:
                for iid, item in list(st.session_state.grill_items.items()):
                    with st.container(border=True):
                        c_a, c_b = st.columns([0.8, 0.2])
                        c_a.markdown(f"**{item['name']}** ({item['done_level']})")
                        if c_b.button("🗑️", key=f"del_{iid}"):
                            del st.session_state.grill_items[iid]
                            st.rerun()

                        if item['phase'] == "waiting":
                            if st.button("▶️ התחל טיימר", key=f"btn_{iid}"):
                                item['phase'] = "side1"
                                item['end_time'] = time.time() + item['side_time']
                                st.rerun()
                        elif item['phase'] in ["side1", "side2", "resting"]:
                            rem = max(0, item['end_time'] - time.time())
                            if item['phase'] == "side1":
                                st.warning("🟠 צד א' - צריבה ראשונית")
                            elif item['phase'] == "side2":
                                st.error("🔴 צד ב' - סגירת הנתח")
                            else:
                                st.success("🟢 מנוחה - מיצים נספגים")

                            total_time = item['rest_time'] if item['phase'] == "resting" else item['side_time']
                            st.progress(min(1.0, 1.0 - (rem / total_time)))

                            if rem == 0:
                                if item['phase'] == "side1":
                                    item['phase'], item['end_time'] = "side2", time.time() + item['side_time']
                                    play_flip_sound()
                                elif item['phase'] == "side2":
                                    if item['rest_time'] > 0:
                                        item['phase'], item['end_time'] = "resting", time.time() + item['rest_time']
                                    else:
                                        item['phase'], item['done_time'] = "done", time.time()
                                    play_done_sound()
                                elif item['phase'] == "resting":
                                    item['phase'], item['done_time'] = "done", time.time()
                                    play_done_sound()
                                st.rerun()

                            m, s = divmod(int(rem), 60)
                            st.metric("זמן נותר", f"{m:02d}:{s:02d}")

                        elif item['phase'] == "done":
                            st.success("✅ מוכן!")
                            if time.time() - item['done_time'] > 10:
                                st.session_state.history_log.append({
                                    "name": item['name'], "done_level": item['done_level'],
                                    "thickness": item['thickness']
                                })
                                del st.session_state.grill_items[iid]
                                st.rerun()


        render_grill()

st.divider()

# --- 4. מדריך טמפרטורות ---
with st.expander("🌡️ מדריך טמפרטורות פנימיות"):
    col_empty, col_text, col_img = st.columns([1, 1.5, 1])

    with col_img:
        if os.path.exists("steak_guide.jpg"):
            st.image("steak_guide.jpg", caption="מדריך ויזואלי", width=250)

    with col_text:
        st.markdown("""
        ### מה קורה בתוך הסטייק?
        - **Rare (52°C):** מרכז אדום וקר. צריבה חיצונית קלה.
        - **Med-Rare (55°C):** השומן נמס, מרכז ורוד-אדום וחם.
        - **Medium (60°C):** ורוד עז, בשר מוצק ועסיסי.
        - **Med-Well (65°C):** רוב הנתח חום-אפור, רצועה ורודה עדינה מאוד במרכז.
        - **Well Done (71°C+):** אפור-חום, יבש.
        """)

# --- 5. היסטוריה וסנכרון ---
if st.session_state.history_log:
    st.divider()
    st.subheader("📊 היסטוריה וסנכרון")

    c_del, c_thick, c_done, c_name = st.columns([0.5, 1, 1.5, 1.5])
    c_name.markdown("**סוג הנתח**")
    c_done.markdown("**מידת עשייה**")
    c_thick.markdown("**עובי**")
    c_del.markdown("<div style='text-align: center;'><b>מחק</b></div>", unsafe_allow_html=True)
    st.divider()

    for i, record in enumerate(st.session_state.history_log):
        with st.container():
            col_del, col_thick, col_done, col_name = st.columns([0.5, 1, 1.5, 1.5])
            col_name.write(record['name'])
            col_done.write(record['done_level'])
            col_thick.write(f"{record['thickness']} ס''מ")
            if col_del.button("🗑️", key=f"del_hist_{i}", use_container_width=True):
                st.session_state.history_log.pop(i)
                st.rerun()

    st.write("")
    col_export, col_clear = st.columns(2)
    with col_export:
        if st.button("💾 סנכרן ל-Sheets / מנוע החלטות"):
            try:
                res = requests.post(WEBHOOK_URL, json=st.session_state.history_log, timeout=5)
                if res.status_code == 200:
                    st.success("✅ סונכרן בהצלחה!")
                else:
                    st.error(f"❌ שגיאת שרת")
            except:
                st.warning("⚠️ אין חיבור לאינטרנט או שהכתובת שגויה.")
    with col_clear:
        if st.button("🧨 נקה רשימה"):
            st.session_state.history_log = []
            st.rerun()


#פקודת הרצה של הקוד בחלונית הconsol היא streamlit run app.py