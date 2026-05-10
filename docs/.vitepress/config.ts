import { defineConfig } from 'vitepress'

export default defineConfig({
  base: '/econai-agent-platform/',
  lang: 'zh-CN',
  title: '经济金融 AI 智能体课程平台',
  description: '教师发布作业，学生提交，AI 自动批改 — 开箱即用的智能教学平台',

  head: [
    ['link', { rel: 'icon', href: '/econai-agent-platform/logo.png' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    ['link', { href: 'https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Noto+Sans+SC:wght@400;500;700&display=swap', rel: 'stylesheet' }],
  ],

  themeConfig: {
    logo: '/logo.png',
    nav: [
      { text: '指南', link: '/guide/what-is-this' },
      { text: '教师', link: '/guide/for-teachers' },
      { text: '学生', link: '/guide/for-students' },
      { text: 'GitHub', link: 'https://github.com/ai-lingnan/econai-agent-platform' },
    ],

    sidebar: [
      {
        text: '了解平台',
        items: [
          { text: '这个平台是什么', link: '/guide/what-is-this' },
          { text: '功能总览', link: '/guide/features' },
          { text: 'AI 批改是怎么工作的', link: '/guide/ai-grading' },
        ],
      },
      {
        text: '使用指南',
        items: [
          { text: '快速开始', link: '/guide/getting-started' },
          { text: '教师使用指南', link: '/guide/for-teachers' },
          { text: '学生使用指南', link: '/guide/for-students' },
          { text: '环境变量参考', link: '/guide/configuration' },
        ],
      },
      {
        text: '技术文档',
        items: [
          { text: '架构说明', link: '/guide/architecture' },
          { text: '开发指南', link: '/guide/development' },
        ],
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/ai-lingnan/econai-agent-platform' },
    ],

    outline: { label: '目录' },
    docFooter: { prev: '上一篇', next: '下一篇' },
    darkModeSwitchLabel: '主题',
    sidebarMenuLabel: '菜单',
    returnToTopLabel: '回到顶部',
    lastUpdated: { text: '最后更新' },

    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索文档' },
          modal: {
            noResultsText: '无法找到相关结果',
            resetButtonTitle: '清除查询条件',
            footer: { selectText: '选择', navigateText: '切换' },
          },
        },
      },
    },
  },
})
