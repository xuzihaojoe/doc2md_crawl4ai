import { useEffect, useMemo, useState, useDeferredValue, memo, useRef } from 'react'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { api, anonId, type CrawlJob, type Document, type DocumentDetail, type User } from './api'
import {
  Button,
  Card,
  Col,
  Dropdown,
  Descriptions,
  Divider,
  Empty,
  Form,
  Input,
  Layout,
  List,
  Modal,
  Popconfirm,
  Row,
  Space,
  Spin,
  Tag,
  Typography,
  message
} from 'antd'
import {
  DeleteOutlined,
  DownloadOutlined,
  LoginOutlined,
  LogoutOutlined,
  MoreOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
  SearchOutlined,
  SendOutlined
} from '@ant-design/icons'

const { Header, Content } = Layout
const { Text } = Typography

function MdView({ md }: { md: string }) {
  const deferredMd = useDeferredValue(md)
  const html = useMemo(() => {
    const raw = marked.parse(deferredMd, { breaks: true }) as string
    return DOMPurify.sanitize(raw)
  }, [deferredMd])
  return <div className="md" dangerouslySetInnerHTML={{ __html: html }} />
}

const MemoMdView = memo(MdView)

function statusTag(status: string) {
  if (status === 'running' || status === 'pending') return <Tag color="processing">{status}</Tag>
  if (status === 'succeeded') return <Tag color="success">{status}</Tag>
  if (status === 'failed') return <Tag color="error">{status}</Tag>
  return <Tag>{status}</Tag>
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [jobs, setJobs] = useState<CrawlJob[]>([])
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [docs, setDocs] = useState<Document[]>([])
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null)
  const [docDetail, setDocDetail] = useState<DocumentDetail | null>(null)
  const [jobName, setJobName] = useState('')
  const [startUrl, setStartUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [polling, setPolling] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [jobQuery, setJobQuery] = useState('')
  const [docQuery, setDocQuery] = useState('')
  const [helpOpen, setHelpOpen] = useState(false)
  const prevJobStatusRef = useRef<string | null>(null)

  const [authForm] = Form.useForm()

  async function refreshJobs(autoSelectFirstWhenEmpty: boolean = true) {
    const j = await api.listCrawls()
    setJobs(j)
    // 默认行为：首次进入页面时，自动选中第一个任务，方便用户直接浏览
    // 但在“删除当前任务”这类场景，我们会传 autoSelectFirstWhenEmpty=false，
    // 避免删除后又立刻选中另一个任务导致用户误以为“文档列表没清空”。
    if (autoSelectFirstWhenEmpty && !selectedJobId && j.length) setSelectedJobId(j[0].id)
  }

  useEffect(() => {
    ;(async () => {
      try {
        setUser(await api.me())
      } catch {
        setUser(null)
      }
      try {
        await refreshJobs()
      } catch (e: any) {
        message.error(e.message)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const selectedJob = useMemo(() => jobs.find((j) => j.id === selectedJobId) || null, [jobs, selectedJobId])
  const selectedJobRunning = selectedJob ? selectedJob.status === 'running' || selectedJob.status === 'pending' : false

  // 更新前一个状态引用
  useEffect(() => {
    if (selectedJob) {
      prevJobStatusRef.current = selectedJob.status
    }
  }, [selectedJob])

  // 自动轮询：选中的任务在跑时，2s 刷新一次
  useEffect(() => {
    if (!selectedJobId) return
    let timer: any = null
    async function tick() {
      try {
        setPolling(true)
        const prevStatus = prevJobStatusRef.current
        await refreshJobs()
        // 检查任务是否刚完成
        if (prevStatus && (prevStatus === 'running' || prevStatus === 'pending')) {
          const updatedJob = jobs.find(j => j.id === selectedJobId)
          if (updatedJob && updatedJob.status === 'succeeded') {
            // 任务完成，刷新文档列表
            const d = await api.listDocuments(selectedJobId as string)
            setDocs(d)
            const merged = d.find((x) => x.is_merged) || d[0]
            setSelectedDocId(merged ? merged.id : null)
            message.success('抓取完成！')
          }
        }
      } catch {
        // ignore
      } finally {
        setPolling(false)
      }
    }
    tick()
    if (selectedJobRunning) timer = setInterval(tick, 2000)
    return () => timer && clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedJobId, selectedJobRunning])

  useEffect(() => {
    ;(async () => {
      if (!selectedJobId) {
        setDocs([])
        return
      }
      try {
        const d = await api.listDocuments(selectedJobId)
        setDocs(d)
        const merged = d.find((x) => x.is_merged) || d[0]
        setSelectedDocId(merged ? merged.id : null)
      } catch (e: any) {
        message.error(e.message)
      }
    })()
  }, [selectedJobId])

  useEffect(() => {
    ;(async () => {
      if (!selectedDocId) {
        setDocDetail(null)
        return
      }
      try {
        setDocDetail(await api.getDocument(selectedDocId))
      } catch (e: any) {
        message.error(e.message)
      }
    })()
  }, [selectedDocId])

  async function onCreateCrawl() {
    if (!jobName.trim()) {
      message.warning('请输入任务名称')
      return
    }
    if (!startUrl.trim()) {
      message.warning('请输入要抓取的URL')
      return
    }
    setLoading(true)
    try {
      const job = await api.createCrawl(jobName.trim(), startUrl.trim())
      setJobName('')
      setStartUrl('')
      message.success('已提交抓取任务')
      await refreshJobs()
      setSelectedJobId(job.id)
    } catch (e: any) {
      message.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function onAuthSubmit() {
    setLoading(true)
    try {
      const { username, password } = await authForm.validateFields()
      const u = authMode === 'login' ? await api.login(username, password) : await api.register(username, password)
      setUser(u)
      message.success(authMode === 'login' ? '登录成功' : '注册成功')
      setAuthOpen(false)
      await refreshJobs()
    } catch (e: any) {
      if (e?.errorFields) return
      message.error(e.message || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  async function onLogout() {
    setLoading(true)
    try {
      await api.logout()
      setUser(null)
      message.success('已退出')
      await refreshJobs()
    } catch (e: any) {
      message.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function onDeleteJob(jobId: string) {
    try {
      await api.deleteCrawl(jobId)
      message.success('已删除任务（含其文档）')
      // 如果删的是当前选中任务，清空右侧
      if (jobId === selectedJobId) {
        setSelectedJobId(null)
        setDocs([])
        setSelectedDocId(null)
        setDocDetail(null)
      }
      // 删除当前任务时，不自动切到另一个任务（避免用户困惑）
      await refreshJobs(jobId !== selectedJobId)
    } catch (e: any) {
      message.error(e.message || '删除失败')
    }
  }

  async function onDeleteDoc(docId: number) {
    try {
      await api.deleteDocument(docId)
      message.success('已删除文档')
      if (docId === selectedDocId) {
        setSelectedDocId(null)
        setDocDetail(null)
      }
      if (selectedJobId) {
        const d = await api.listDocuments(selectedJobId)
        setDocs(d)
        if (!selectedDocId) {
          const merged = d.find((x) => x.is_merged) || d[0]
          if (merged) setSelectedDocId(merged.id)
        }
      }
    } catch (e: any) {
      message.error(e.message || '删除失败')
    }
  }

  const filteredJobs = useMemo(() => {
    const q = jobQuery.trim().toLowerCase()
    if (!q) return jobs
    return jobs.filter((j) => j.start_url.toLowerCase().includes(q) || j.status.toLowerCase().includes(q))
  }, [jobs, jobQuery])

  const filteredDocs = useMemo(() => {
    const q = docQuery.trim().toLowerCase()
    if (!q) return docs
    return docs.filter((d) => d.title.toLowerCase().includes(q) || d.url.toLowerCase().includes(q))
  }, [docs, docQuery])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 16px' }}>
        <Row align="middle" justify="space-between" gutter={12}>
          <Col>
            <Space size="middle">
              <Typography.Title level={4} style={{ margin: 0 }}>
                doc2md 管理台
              </Typography.Title>
              <Text type="secondary" style={{ fontSize: 12 }}>
                匿名会话：<Text code>{anonId}</Text>
              </Text>
            </Space>
          </Col>
          <Col flex="auto">
            <Space style={{ width: '100%' }} direction="horizontal">
              <Input
                style={{ width: 150 }}
                value={jobName}
                onChange={(e) => setJobName(e.target.value)}
                placeholder="任务名称"
                onPressEnter={onCreateCrawl}
              />
              <Input
                style={{ width: 300 }}
                value={startUrl}
                onChange={(e) => setStartUrl(e.target.value)}
                placeholder="输入要抓取的 URL（入口页）"
                onPressEnter={onCreateCrawl}
              />
              <Button type="primary" icon={<SendOutlined />} loading={loading} onClick={onCreateCrawl}>
                开始抓取
              </Button>
              <Button type="link" icon={<QuestionCircleOutlined />} onClick={() => setHelpOpen(true)}>
                使用说明
              </Button>
            </Space>
          </Col>
          <Col>
            <Space>
              {user ? (
                <>
                  <Text>已登录：{user.username}</Text>
                  <Button icon={<LogoutOutlined />} onClick={onLogout} loading={loading}>
                    退出
                  </Button>
                </>
              ) : (
                <Button type="default" icon={<LoginOutlined />} onClick={() => setAuthOpen(true)}>
                  登录 / 注册
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </Header>

      <Content style={{ padding: 16 }}>
        <Row gutter={16}>
          <Col xs={24} lg={8}>
            <Card
              title="抓取任务"
              size="small"
              bodyStyle={{ padding: 12 }}
              extra={selectedJob ? statusTag(selectedJob.status) : null}
            >
              {/* 让左侧滚动独立，不影响右侧 */}
              <div style={{ height: 'calc(100vh - 170px)', display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* Jobs */}
                <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, flex: 1 }}>
                  <Input
                    allowClear
                    prefix={<SearchOutlined />}
                    placeholder="搜索任务"
                    value={jobQuery}
                    onChange={(e) => setJobQuery(e.target.value)}
                  />
                  <Divider style={{ margin: '12px 0' }} />
                  <div style={{ overflow: 'auto', paddingRight: 4 }}>
                    {filteredJobs.length === 0 ? (
                      <Empty description="暂无任务" />
                    ) : (
                      <List
                        size="small"
                        dataSource={filteredJobs}
                        renderItem={(j) => (
                          <List.Item
                            onClick={() => {
                              setSelectedJobId(j.id)
                              setDocQuery('')
                            }}
                            style={{
                              cursor: 'pointer',
                              background: j.id === selectedJobId ? 'rgba(22,119,255,0.08)' : undefined,
                              borderRadius: 8,
                              padding: '8px 10px'
                            }}
                            actions={[
                              <Dropdown
                                key="more"
                                trigger={['click']}
                                menu={{
                                  items: [
                                    {
                                      key: 'download',
                                      label: '下载任务压缩包',
                                      icon: <DownloadOutlined />,
                                      onClick: async () => {
                                        try {
                                          await api.downloadCrawlZip(j.id)
                                        } catch (e: any) {
                                          message.error(e.message || '下载失败')
                                        }
                                      }
                                    },
                                    {
                                      key: 'delete',
                                      danger: true,
                                      label: (
                                        <Popconfirm
                                          title="删除任务"
                                          description="将删除该任务及其所有文档，确定继续？"
                                          okText="删除"
                                          cancelText="取消"
                                          onConfirm={() => onDeleteJob(j.id)}
                                        >
                                          删除任务
                                        </Popconfirm>
                                      ),
                                      icon: <DeleteOutlined />
                                    }
                                  ]
                                }}
                              >
                                <Button size="small" type="text" icon={<MoreOutlined />} onClick={(e) => e.stopPropagation()} />
                              </Dropdown>
                            ]}
                          >
                            <List.Item.Meta
                              title={
                                <Space size="small" wrap>
                                  {statusTag(j.status)}
                                  <Text strong>{j.name}</Text>
                                </Space>
                              }
                              description={
                                <Space direction="vertical" size={0}>
                                  <Text ellipsis style={{ maxWidth: 240 }}>
                                    {j.start_url}
                                  </Text>
                                  {j.error ? <Text type="danger">{j.error}</Text> : null}
                                </Space>
                              }
                            />
                          </List.Item>
                        )}
                      />
                    )}
                  </div>
                </div>

                {/* Docs for selected job */}
                <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, flex: 1 }}>
                  <Space direction="vertical" size={0}>
                    <Text strong>文档列表（当前任务）</Text>
                    <Text type="secondary" ellipsis>
                      {selectedJob ? selectedJob.start_url : '请先选择一个抓取任务'}
                    </Text>
                  </Space>
                  <div style={{ height: 8 }} />
                  <Input
                    allowClear
                    prefix={<SearchOutlined />}
                    placeholder="搜索文档"
                    value={docQuery}
                    onChange={(e) => setDocQuery(e.target.value)}
                    disabled={!selectedJobId}
                  />
                  <Divider style={{ margin: '12px 0' }} />
                  <div style={{ overflow: 'auto', paddingRight: 4 }}>
                    {selectedJobRunning ? (
                      <Space style={{ marginBottom: 12 }}>
                        <Spin size="small" /> <Text type="secondary">抓取中…</Text>
                      </Space>
                    ) : null}

                    {!selectedJobId ? (
                      <Empty description="请选择左侧任务" />
                    ) : filteredDocs.length === 0 ? (
                      <Empty description="暂无文档" />
                    ) : (
                      <List
                        size="small"
                        dataSource={filteredDocs}
                        renderItem={(d) => (
                          <List.Item
                            onClick={() => setSelectedDocId(d.id)}
                            style={{
                              cursor: 'pointer',
                              background: d.id === selectedDocId ? 'rgba(22,119,255,0.08)' : undefined,
                              borderRadius: 8,
                              padding: '8px 10px'
                            }}
                            actions={[
                              <Button
                                key="download"
                                size="small"
                                type="link"
                                icon={<DownloadOutlined />}
                                onClick={async (e) => {
                                  e.stopPropagation()
                                  try {
                                    await api.downloadDocument(d.id, d.is_merged ? 'merged' : d.title)
                                  } catch (err: any) {
                                    message.error(err.message || '下载失败')
                                  }
                                }}
                              >
                                下载
                              </Button>,
                              <Popconfirm
                                key="delete"
                                title="删除文档"
                                okText="删除"
                                cancelText="取消"
                                onConfirm={() => onDeleteDoc(d.id)}
                              >
                                <Button
                                  size="small"
                                  type="link"
                                  danger
                                  icon={<DeleteOutlined />}
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  删除
                                </Button>
                              </Popconfirm>
                            ]}
                          >
                            <Space direction="vertical" size={2} style={{ width: '100%' }}>
                              <Space>
                                {d.is_merged ? <Tag color="geekblue">merged</Tag> : <Tag>page</Tag>}
                                <Text strong>{d.is_merged ? 'merged' : d.title}</Text>
                              </Space>
                              <Text type="secondary" ellipsis style={{ maxWidth: 280 }}>
                                {d.url}
                              </Text>
                            </Space>
                          </List.Item>
                        )}
                      />
                    )}
                  </div>
                </div>
              </div>
            </Card>
          </Col>

          <Col xs={24} lg={16}>
            <Card
              title="Markdown 预览"
              size="small"
              extra={
                docDetail ? (
                  <Space>
                    <Button size="small" href={docDetail.url} target="_blank">
                      打开来源
                    </Button>
                    <Button
                      size="small"
                      icon={<DownloadOutlined />}
                      onClick={async () => {
                        try {
                          await api.downloadDocument(docDetail.id, docDetail.is_merged ? 'merged' : docDetail.title)
                        } catch (e: any) {
                          message.error(e.message || '下载失败')
                        }
                      }}
                    >
                      下载 MD
                    </Button>
                    {docDetail.qiniu_url ? (
                      <Button size="small" href={docDetail.qiniu_url} target="_blank" type="primary">
                        七牛链接
                      </Button>
                    ) : null}
                  </Space>
                ) : null
              }
            >
              {selectedJob ? (
                <Descriptions size="small" column={1} style={{ marginBottom: 12 }}>
                  <Descriptions.Item label="任务状态">{statusTag(selectedJob.status)}</Descriptions.Item>
                  <Descriptions.Item label="入口 URL">{selectedJob.start_url}</Descriptions.Item>
                </Descriptions>
              ) : null}

              {docDetail ? (
                <div style={{ maxHeight: '72vh', overflow: 'auto' }}>
                  <MemoMdView md={docDetail.markdown_text} />
                </div>
              ) : (
                <Empty description="请选择左侧文档进行预览" />
              )}
            </Card>
          </Col>
        </Row>
      </Content>

      <Modal
        title={authMode === 'login' ? '登录' : '注册'}
        open={authOpen}
        onCancel={() => setAuthOpen(false)}
        onOk={onAuthSubmit}
        confirmLoading={loading}
        okText={authMode === 'login' ? '登录' : '注册'}
      >
        <Space style={{ marginBottom: 12 }}>
          <Button type={authMode === 'login' ? 'primary' : 'default'} onClick={() => setAuthMode('login')}>
            登录
          </Button>
          <Button type={authMode === 'register' ? 'primary' : 'default'} onClick={() => setAuthMode('register')}>
            注册
          </Button>
        </Space>
        <Form
          form={authForm}
          layout="vertical"
          initialValues={{ username: '', password: '' }}
        >
          <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="使用说明" open={helpOpen} onCancel={() => setHelpOpen(false)} footer={null}>
        <Typography.Paragraph>
          1）<Text strong>以 / 结尾</Text>：抓取该目录下的页面（只抓这个目录前缀，不会爬到同级目录）。
        </Typography.Paragraph>
        <Typography.Paragraph>
          例如：<Text code>https://doc.dcloud.net.cn/uni-app-x/uts/</Text> 会抓取 <Text code>/uts/</Text> 下面的文档。
        </Typography.Paragraph>
        <Typography.Paragraph>
          2）<Text strong>不以 / 结尾</Text>：默认只抓取当前页面（更安全）。
        </Typography.Paragraph>
        <Typography.Paragraph>
          例如：<Text code>https://doc.dcloud.net.cn/uni-app-x/collocation/pagesjson.html</Text> 只抓这一个页面。
        </Typography.Paragraph>
        <Typography.Paragraph type="secondary">
          提示：如果你想手动控制抓取范围（include/exclude 正则），我也可以把高级选项加到界面里。
        </Typography.Paragraph>
      </Modal>
    </Layout>
  )
}
