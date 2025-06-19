import streamlit as st
import requests
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from datetime import datetime
import time
from io import BytesIO
from streamlit_paste_button import paste_image_button as pbutton
import base64

API_URL = "http://localhost:8000"

st.set_page_config(page_title="AI 助理任务管理平台", layout="wide")

# 初始化session state
if "pasted_images" not in st.session_state:
    st.session_state["pasted_images"] = []
if "form_submitted" not in st.session_state:
    st.session_state["form_submitted"] = False
if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = []

def handle_paste_image():
    try:
        paste_result = pbutton("📋 粘贴图片", key="paste_button")
        if paste_result and paste_result.image_data is not None:
            # 将图片数据转换为base64以便于存储和显示
            buffered = BytesIO()
            paste_result.image_data.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            # 去重：只有新图片才加入
            existed_base64 = [img["base64"] for img in st.session_state["pasted_images"]]
            if img_str not in existed_base64:
                st.session_state["pasted_images"].append({
                    "image": paste_result.image_data,
                    "base64": img_str
                })
                st.success("图片已成功粘贴！")
            else:
                st.info("该图片已粘贴，无需重复添加。")
    except Exception as e:
        st.error(f"粘贴图片时出错: {str(e)}")

def display_pasted_images():
    if st.session_state["pasted_images"]:
        st.write("已粘贴图片：")
        cols = st.columns(3)  # 每行显示3张图片
        for idx, img_data in enumerate(st.session_state["pasted_images"]):
            with cols[idx % 3]:
                st.image(img_data["image"], caption=f"第{idx+1}张", use_column_width=True)
    else:
        pass
        #st.rerun()

def reset_form():
    st.session_state["form_title"] = ""
    st.session_state["form_type"] = "知识库"
    st.session_state["form_status"] = "pending"
    st.session_state["form_priority"] = "normal"
    st.session_state["form_tags"] = ""
    st.session_state["form_desc"] = ""
    st.session_state["form_completed_at"] = None
    st.session_state["form_file"] = None
    st.session_state["pasted_images"] = []
    st.session_state["uploaded_files"] = []

# ========== 添加任务页面 ==========
if 'page' not in st.session_state:
    st.session_state['page'] = '任务查询'

page = st.sidebar.radio("选择页面", ["任务查询", "AI任务会话", "添加任务"], key='page')

# ========== 任务查询页面 ==========
if page == "任务查询":
    st.title("任务查询")
    # ========== 查询条件区 ==========
    with st.form("query_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            search = st.text_input("关键词（标题/描述/标签）")
        with col2:
            status_filter = st.multiselect("状态", ["pending", "in_progress", "completed", "paused"])
        with col3:
            date_range = st.date_input("创建时间区间", [])
        submit = st.form_submit_button("查询")
    r = requests.get(f"{API_URL}/tasks/")
    if r.status_code == 200:
        tasks = r.json()
        if tasks:
            df = pd.DataFrame([{
                "ID": t["id"],
                "名称": t["title"],
                "类型": "知识库" if t["type"] == "knowledge" else "工作记录",
                "描述": t["description"],
                "状态": t["status"],
                "优先级": t["priority"],
                "标签": t["tags"],
                "创建时间": t["created_at"][:19].replace('T', ' ') if t["created_at"] else "",
                "修改时间": t["updated_at"][:19].replace('T', ' ') if t["updated_at"] else "",
                "完成时间": t["completed_at"][:19].replace('T', ' ') if t["completed_at"] else "" if t["type"] == "work" else "",
                "操作": ""
            } for t in tasks])
            if submit:
                if search:
                    df = df[df[["名称", "描述", "标签"]].apply(lambda x: x.str.contains(search, na=False), axis=1).any(axis=1)]
                if status_filter:
                    df = df[df["状态"].isin(status_filter)]
                if date_range and len(date_range) == 2:
                    start, end = date_range
                    df = df[(df["创建时间"] >= str(start)) & (df["创建时间"] <= str(end))]
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_pagination(paginationAutoPageSize=True)
            gb.configure_default_column(editable=False, groupable=True)
            gb.configure_column("操作", header_name="操作", cellRenderer=JsCode('''
                function(params) {
                    return `<button id='edit-btn'>编辑</button> <button id='del-btn'>删除</button>`
                }
            '''), editable=False, filter=False, sortable=False, width=120)
            gb.configure_selection('single')
            grid_options = gb.build()
            grid_response = AgGrid(
                df,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                allow_unsafe_jscode=True,
                fit_columns_on_grid_load=True,
                theme='alpine',
                enable_enterprise_modules=False
            )
            selected = grid_response['selected_rows']
            if selected is not None and isinstance(selected, list) and len(selected) > 0:
                sel = selected[0]
                task_id = sel['ID']
                st.markdown(f"---\n**任务ID:** {sel['ID']}  **名称:** {sel['名称']}  **类型:** {sel['类型']}  **状态:** {sel['状态']}")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if sel['状态'] != 'completed' and st.button(f"标记完成_{task_id}"):
                        update = {"status": "completed"}
                        requests.put(f"{API_URL}/tasks/{task_id}", json=update)
                        st.rerun()
                with col2:
                    if sel['状态'] != 'in_progress' and st.button(f"设为进行中_{task_id}"):
                        update = {"status": "in_progress"}
                        requests.put(f"{API_URL}/tasks/{task_id}", json=update)
                        st.rerun()
                with col3:
                    if sel['状态'] != 'paused' and st.button(f"设为暂停_{task_id}"):
                        update = {"status": "paused"}
                        requests.put(f"{API_URL}/tasks/{task_id}", json=update)
                        st.rerun()
                with col4:
                    if st.button(f"删除_{task_id}"):
                        requests.delete(f"{API_URL}/tasks/{task_id}")
                        st.rerun()
                # 附件上传与管理
                st.write("附件：")
                st.markdown(
                    """
                    **提示：**
                    - 支持多选和粘贴图片（部分浏览器可直接Ctrl+V粘贴截图）
                    - 推荐直接拖拽图片文件到上传区域
                    - 点击上传区会弹出文件选择窗口
                    """
                )
                if "pasted_images" not in st.session_state:
                    st.session_state["pasted_images"] = []

                handle_paste_image()
                display_pasted_images()
                # 展示附件及删除按钮
                task = next((t for t in tasks if t['id'] == task_id), None)
                if task and task['attachments']:
                    for att in task['attachments']:
                        download_url = f"{API_URL}/attachments/{att['id']}/download"
                        st.write(f"{att['filename']} ({att['filetype']}) [下载附件]({download_url})")
                        del_btn_key = f"del_btn_{att['id']}_{task_id}"
                        confirm_key = f"confirm_del_{att['id']}_{task_id}"
                        if st.button("删除", key=del_btn_key):
                            st.session_state[confirm_key] = True
                        if st.session_state.get(confirm_key, False):
                            st.warning("确定要删除该附件吗？")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("确定删除", key=f"yes_{att['id']}_{task_id}"):
                                    res = requests.delete(f"{API_URL}/attachments/{att['id']}")
                                    if res.status_code == 200:
                                        st.toast("附件删除成功！", icon="✅")
                                        st.session_state[confirm_key] = False
                                        st.rerun()
                                    else:
                                        st.toast("附件删除失败", icon="❌")
                            with col2:
                                if st.button("取消", key=f"no_{att['id']}_{task_id}"):
                                    st.session_state[confirm_key] = False
        else:
            st.info("暂无任务，请先添加或用AI生成任务。")
    else:
        st.error("无法获取任务列表")

# ========== AI任务会话页面 ==========
elif page == "AI任务会话":
    st.title("AI任务添加与统计（会话模式）")
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    if "last_ai_tasks" not in st.session_state:
        st.session_state["last_ai_tasks"] = []
    # 聊天输入区
    user_input = st.text_input("请输入你的需求或目标：", key="ai_chat_input")
    if st.button("发送", key="ai_chat_send"):
        if user_input.strip():
            with st.spinner("AI正在思考..."):
                resp = requests.post(f"{API_URL}/ai_generate_tasks/", json={"prompt": user_input})
            if resp.status_code == 200:
                ai_tasks = resp.json()["tasks"]
                st.session_state["chat_history"].append(("user", user_input))
                st.session_state["chat_history"].append(("ai", ai_tasks))
                st.session_state["last_ai_tasks"] = ai_tasks
                st.rerun()
            else:
                st.error(f"AI生成失败: {resp.text}")
    # 聊天历史区
    for role, content in st.session_state["chat_history"]:
        if role == "user":
            st.markdown(f"<div style='background:#e6f7ff;padding:8px 12px;border-radius:8px;margin-bottom:4px;'><b>你：</b> {content}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='background:#f6ffed;padding:8px 12px;border-radius:8px;margin-bottom:4px;'><b>AI：</b></div>", unsafe_allow_html=True)
            for t in content:
                st.markdown(f"<div style='background:#fffbe6;padding:4px 12px;border-radius:6px;margin-bottom:2px;'>- <b>{t['title']}</b>: {t['description']}</div>", unsafe_allow_html=True)
    # 任务统计区
    st.markdown("---")
    st.subheader("任务统计")
    r = requests.get(f"{API_URL}/tasks/")
    if r.status_code == 200:
        tasks = r.json()
        total = len(tasks)
        completed = len([t for t in tasks if t['status'] == 'completed'])
        pending = len([t for t in tasks if t['status'] == 'pending'])
        in_progress = len([t for t in tasks if t['status'] == 'in_progress'])
        paused = len([t for t in tasks if t['status'] == 'paused'])
        st.write(f"**总任务数：** {total}")
        st.write(f"**已完成：** {completed}")
        st.write(f"**未完成：** {pending}")
        st.write(f"**进行中：** {in_progress}")
        st.write(f"**已暂停：** {paused}")
    else:
        st.error("无法获取任务统计信息")

    # ========== AI数据分析区 ==========
    st.markdown("---")
    st.subheader("AI数据分析")
    analysis_input = st.text_area("请输入你的数据分析需求：", key="ai_analysis_input")
    if st.button("提交分析", key="ai_analysis_btn"):
        if analysis_input.strip():
            with st.spinner("AI正在分析..."):
                resp = requests.post(f"{API_URL}/ai_data_analysis/", json={"prompt": analysis_input})
            if resp.status_code == 200:
                result = resp.json()["result"]
                st.success("分析结果：")
                st.markdown(result)
            else:
                st.error(f"AI分析失败: {resp.text}")

# ========== 添加任务页面 ==========
elif page == "添加任务":
    st.title("添加任务")
    with st.form("add_task_form"):
        title = st.text_input("任务名称", value=st.session_state.get("form_title", ""), key="form_title")
        type_ = st.selectbox("任务类型", ["知识库", "工作记录"], index=0 if st.session_state.get("form_type", "知识库") == "知识库" else 1, key="form_type")
        status = st.selectbox("状态", ["pending", "in_progress", "completed", "paused"], index=["pending", "in_progress", "completed", "paused"].index(st.session_state.get("form_status", "pending")), key="form_status")
        priority = st.selectbox("优先级", ["low", "normal", "high"], index=["low", "normal", "high"].index(st.session_state.get("form_priority", "normal")), key="form_priority")
        tags = st.text_input("标签（逗号分隔）", value=st.session_state.get("form_tags", ""), key="form_tags")
        description = st.text_area("任务描述", value=st.session_state.get("form_desc", ""), key="form_desc")
        completed_at = None
        if type_ == "工作记录":
            completed_at = st.date_input("完成时间（可选）", key="form_completed_at")
        st.markdown("""
        **提示：**
        - 支持拖拽图片或文件到上传区
        - 支持常见图片、文档、表格等格式
        """)
        uploaded_files = st.file_uploader(
            "上传附件（支持多选和图片）",
            type=None,
            accept_multiple_files=True,
            key="form_file"
        )
        submitted = st.form_submit_button("添加任务")

    st.markdown("---")
    st.subheader("粘贴图片")
 

    st.write("图片长度：", len((st.session_state.get("pasted_images", []))))

    if st.button("清空所有粘贴图片"):
        st.session_state["pasted_images"] = []
        st.rerun()
    handle_paste_image()
    display_pasted_images()

    if submitted:
        data = {
            "title": title,
            "description": description,
            "type": "work" if type_ == "工作记录" else "knowledge",
            "status": status,
            "priority": priority,
            "tags": tags,
        }
        if type_ == "工作记录" and completed_at:
            data["completed_at"] = str(completed_at)
        r_add = requests.post(f"{API_URL}/tasks/", json=data)
        if r_add.status_code == 200:
            task_id = r_add.json()["id"]
            all_success = True
            # 上传file_uploader选中的文件
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    if uploaded_file.type.startswith("image"):
                        st.image(uploaded_file, caption=uploaded_file.name, width=150)
                    else:
                        st.write(f"已选择文件：{uploaded_file.name}")
                    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                    res = requests.post(f"{API_URL}/tasks/{task_id}/attachments/", files=files)
                    if res.status_code == 200:
                        st.toast(f"附件 {uploaded_file.name} 上传成功！", icon="✅")
                    else:
                        st.toast(f"附件 {uploaded_file.name} 上传失败", icon="❌")
                        all_success = False
            # 上传所有粘贴图片
            #st.write("图片长度：", len(session_state.get("pasted_images", [])))
            for idx, img_data in enumerate(st.session_state.get("pasted_images", [])):
                buf = BytesIO()
                img_data["image"].save(buf, format="PNG")
                buf.seek(0)
                files = {"file": (f"pasted_{idx+1}.png", buf, "image/png")}
                res = requests.post(f"{API_URL}/tasks/{task_id}/attachments/", files=files)
                if res.status_code == 200:
                    st.toast(f"粘贴图片{idx+1}上传成功！", icon="✅")
                else:
                    st.toast(f"粘贴图片{idx+1}上传失败", icon="❌")
                    all_success = False
            st.success("任务添加成功！")
            st.session_state.clear()
            st.rerun()
        else:
            st.toast("添加失败", icon="❌")
