import streamlit as st
import requests
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from datetime import datetime

API_URL = "http://localhost:8000"

st.title("AI 助理任务管理平台（表格版）")

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

# ========== AI生成任务 ==========
st.header("AI生成任务")
ai_prompt = st.text_input("请输入目标或需求，AI将自动拆解为任务：")
if st.button("AI生成任务"):
    if not ai_prompt.strip():
        st.warning("请输入内容！")
    else:
        with st.spinner("AI正在生成任务..."):
            resp = requests.post(f"{API_URL}/ai_generate_tasks/", json={"prompt": ai_prompt})
        if resp.status_code == 200:
            tasks = resp.json()["tasks"]
            st.success(f"成功生成{len(tasks)}个任务！")
            for t in tasks:
                st.write(f"- {t['title']}: {t['description']}")
            st.rerun()
        else:
            st.error(f"AI生成失败: {resp.text}")

# ========== 新建任务（手动） ==========
st.header("新建任务")
title = st.text_input("任务标题")
description = st.text_area("任务描述")
priority = st.selectbox("优先级", ["low", "normal", "high"])
tags = st.text_input("标签（逗号分隔）")
if st.button("添加任务"):
    data = {
        "title": title,
        "description": description,
        "priority": priority,
        "tags": tags
    }
    r = requests.post(f"{API_URL}/tasks/", json=data)
    if r.status_code == 200:
        st.success("任务添加成功！")
        st.rerun()
    else:
        st.error("添加失败")

# ========== 任务表格区 ==========
st.header("任务列表")
r = requests.get(f"{API_URL}/tasks/")
if r.status_code == 200:
    tasks = r.json()
    if tasks:
        # 转为DataFrame
        df = pd.DataFrame([{
            "ID": t["id"],
            "标题": t["title"],
            "描述": t["description"],
            "状态": t["status"],
            "优先级": t["priority"],
            "标签": t["tags"],
            "创建时间": t["created_at"][:10] if t["created_at"] else "",
            "完成时间": t["completed_at"][:10] if t["completed_at"] else "",
            "操作": ""
        } for t in tasks])
        # 按条件筛选
        if submit:
            if search:
                df = df[df[["标题", "描述", "标签"]].apply(lambda x: x.str.contains(search, na=False), axis=1).any(axis=1)]
            if status_filter:
                df = df[df["状态"].isin(status_filter)]
            if date_range and len(date_range) == 2:
                start, end = date_range
                df = df[(df["创建时间"] >= str(start)) & (df["创建时间"] <= str(end))]
        # st-aggrid配置
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
            st.markdown(f"---\n**任务ID:** {sel['ID']}  **标题:** {sel['标题']}  **状态:** {sel['状态']}")
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
            upload_key = f"file_{task_id}"
            show_upload_key = f"show_upload_{task_id}"
            if show_upload_key not in st.session_state:
                st.session_state[show_upload_key] = True
            if st.session_state[show_upload_key]:
                uploaded_file = st.file_uploader(f"上传附件_{task_id}", key=upload_key)
                if uploaded_file is not None:
                    colu1, colu2 = st.columns(2)
                    with colu1:
                        if st.button(f"确定上传_{task_id}"):
                            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                            res = requests.post(f"{API_URL}/tasks/{task_id}/attachments/", files=files)
                            if res.status_code == 200:
                                st.success("附件上传成功！")
                                st.session_state[show_upload_key] = False
                                st.rerun()
                            else:
                                st.error("附件上传失败")
                    with colu2:
                        if st.button(f"取消上传_{task_id}"):
                            st.session_state[show_upload_key] = False
                            st.rerun()
            else:
                if st.button(f"重新上传_{task_id}"):
                    st.session_state[show_upload_key] = True
                    st.rerun()
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
                                    st.success("附件删除成功！")
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                                else:
                                    st.error("附件删除失败")
                        with col2:
                            if st.button("取消", key=f"no_{att['id']}_{task_id}"):
                                st.session_state[confirm_key] = False
    else:
        st.info("暂无任务，请先添加或用AI生成任务。")
else:
    st.error("无法获取任务列表") 