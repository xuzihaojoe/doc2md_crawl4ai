export type User = { id: number; username: string }
export type CrawlJob = {
  id: string
  name: string
  start_url: string
  status: string
  error?: string | null
  created_at: string
  finished_at?: string | null
}
export type Document = {
  id: number
  job_id: string
  title: string
  url: string
  doc_index: number
  is_merged: boolean
  qiniu_url?: string | null
  created_at: string
}
export type DocumentDetail = Document & { markdown_text: string }

function randomId(): string {
  // 兼容部分运行环境没有 crypto.randomUUID 的情况
  const anyCrypto = globalThis.crypto as any
  if (anyCrypto && typeof anyCrypto.randomUUID === 'function') return anyCrypto.randomUUID()
  // fallback：不保证强随机，但足够做“临时匿名会话 id”
  return 'anon-' + Math.random().toString(16).slice(2) + Date.now().toString(16)
}

// 匿名会话：只保存在内存里，刷新页面会变
export const anonId = randomId()

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {})
  headers.set('Content-Type', 'application/json')
  headers.set('X-Anonymous-Id', anonId)
  const res = await fetch(path, { ...init, headers, credentials: 'include' })
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    throw new Error((data && data.detail) || `HTTP ${res.status}`)
  }
  return data as T
}

async function downloadBlob(path: string, filename: string): Promise<void> {
  const headers = new Headers()
  headers.set('X-Anonymous-Id', anonId)
  const res = await fetch(path, { headers, credentials: 'include' })
  if (!res.ok) {
    const text = await res.text()
    let msg = `HTTP ${res.status}`
    try {
      const j = text ? JSON.parse(text) : null
      msg = (j && j.detail) || msg
    } catch {
      // ignore
    }
    throw new Error(msg)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export const api = {
  me: () => req<User | null>('/api/auth/me'),
  register: (username: string, password: string) => req<User>('/api/auth/register', { method: 'POST', body: JSON.stringify({ username, password }) }),
  login: (username: string, password: string) => req<User>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => req<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),

  createCrawl: (name: string, start_url: string) => req<CrawlJob>('/api/crawls', { method: 'POST', body: JSON.stringify({ name, start_url }) }),
  listCrawls: () => req<CrawlJob[]>('/api/crawls'),
  getCrawl: (id: string) => req<CrawlJob>(`/api/crawls/${id}`),
  deleteCrawl: (id: string) => req<{ ok: boolean }>(`/api/crawls/${id}`, { method: 'DELETE' }),
  downloadCrawlZip: async (id: string) => {
    await downloadBlob(`/api/crawls/${id}/download.zip`, `job-${id}.zip`)
  },
  listDocuments: (jobId: string) => req<Document[]>(`/api/crawls/${jobId}/documents`),
  getDocument: (docId: number) => req<DocumentDetail>(`/api/documents/${docId}`),
  deleteDocument: (docId: number) => req<{ ok: boolean }>(`/api/documents/${docId}`, { method: 'DELETE' }),
  downloadDocument: async (docId: number, title: string) => {
    const safe = (title || 'document').replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || 'document'
    await downloadBlob(`/api/documents/${docId}/download`, `${safe}.md`)
  }
}
