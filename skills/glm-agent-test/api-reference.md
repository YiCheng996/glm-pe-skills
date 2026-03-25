# BigModel 智能体 API 参考

服务根路径：`https://open.bigmodel.cn/api/llm-application/open`

## 鉴权

所有请求 Header 加：`Authorization: Bearer <API_KEY>`

## 完整调用流程

```
1. [可选] GET  /v2/application/{app_id}/variables   → 获取输入变量及 upload_unit_id
2. [文件] POST /v2/application/file_upload           → 上传文件，返回 file_id
3. [文件] POST /v2/application/file_stat             → 轮询解析状态（code=1 表示就绪）
4.        POST /v3/application/invoke                → 调用推理，stream=false 时同步返回
```

## 各接口速查

### 1. 获取输入变量 `GET /v2/application/{app_id}/variables`

响应 `data[]` 中每项关键字段：
- `id`：变量 ID（即 upload_unit_id）
- `type`：`input` / `upload_image` / `upload_file` / `upload_audio` / `upload_video`
- `name`：变量名（推理时 content[].key 必须与此一致）

### 2. 文件上传 `POST /v2/application/file_upload`

multipart form-data 字段：

| 字段 | 说明 |
|------|------|
| `app_id` | 应用 ID |
| `upload_unit_id` | 变量 ID（文本类应用必传） |
| `file_type` | 1=excel 2=文档 3=音频 4=图片 5=视频 |
| `files` | 文件二进制（MIME 类型需正确设置） |

响应路径（注意 camelCase）：
```json
{ "data": { "successInfo": [{ "fileId": "xxx", "fileName": "xxx" }],
            "failInfo":    [{ "fileName": "xxx", "failReason": "xxx" }] } }
```

### 3. 文件解析状态 `POST /v2/application/file_stat`

```json
{ "app_id": "xxx", "file_ids": ["id1", "id2"] }
```

响应 `data[]` 中 `code` 含义：`0`=处理中，`1`=成功，`11009`=不存在

> 图片上传后通常直接可用，code 可能返回空列表；脚本等待 2s 后直接进入推理即可。

### 4. 推理接口 `POST /v3/application/invoke`

```json
{
  "app_id": "xxx",
  "stream": false,
  "messages": [{
    "content": [
      { "type": "input",        "value": "用户问题",  "key": "用户输入" },
      { "type": "upload_image", "value": "id1,id2,id3", "key": "图片" }
    ]
  }]
}
```

- `value`：多个文件 ID 用英文逗号拼接
- `key`：必须与智能体变量的 `name` 字段完全一致
- 纯图片智能体不需要 `input` 类型的 content 项

同步响应（`stream: false`）结果路径：
```
choices[0].messages.content.msg   →  string（纯文本）或 dict
choices[0].messages.content.type  →  "text"
```
