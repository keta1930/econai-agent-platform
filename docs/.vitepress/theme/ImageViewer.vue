<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const active = ref(false)
const imgSrc = ref('')
const captionText = ref('')
let cancelTyping: (() => void) | null = null

const CAPTIONS: Record<string, string> = {
  '平台工作流程': '这是平台的完整工作流。教师发布作业并设好评分标准，学生用文本、文件或拍照三种方式提交。提交后两个 AI 同时阅卷——一个按标准逐项打分找不足，一个专门挖掘亮点和创新。几分钟后自动生成包含分数、各维度评价、改进建议和亮点的完整报告。教师在后台看到所有学生的汇总数据。',
  'AI 批改流程': '每份作业提交后，平台会启动两个 AI 同时工作。标准评审按教师设定的评分标准逐维度打分，给出总评和改进建议。亮点发现则专注于找出作业中的创新点和出彩之处，给出附加分。最终分数取两者的较高分——这样即使学生在标准维度上有欠缺，独到的见解也不会被埋没。',
  '角色层级': '平台有三种角色，数据完全隔离。超级管理员在最上层，通过邀请码管理教师账号。每个教师可以创建多个班级，班级之间互相看不到数据——A 班教师看不到 B 班的作业和学生。学生通过教师给的加入凭证注册到具体班级。这种隔离设计让一个平台可以同时服务多个教师、多门课程。',
}

function typeText(text: string) {
  captionText.value = ''
  let i = 0
  const id = setInterval(() => {
    if (i < text.length) {
      captionText.value += text[i]
      i++
    } else {
      clearInterval(id)
      cancelTyping = null
    }
  }, 25)
  cancelTyping = () => { clearInterval(id) }
}

function open(src: string, alt: string) {
  imgSrc.value = src
  captionText.value = ''
  active.value = true
  const desc = CAPTIONS[alt]
  if (desc) {
    setTimeout(() => typeText(desc), 300)
  }
}

function close() {
  if (cancelTyping) { cancelTyping(); cancelTyping = null }
  active.value = false
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && active.value) close()
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)

  document.querySelectorAll<HTMLImageElement>('.clickable-img').forEach(img => {
    img.style.cursor = 'pointer'
    img.addEventListener('click', () => open(img.src, img.alt))
  })
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})

defineExpose({ open })
</script>

<template>
  <Teleport to="body">
    <div v-if="active" class="lightbox" @click.self="close">
      <div class="lightbox-body">
        <img :src="imgSrc" alt="" />
        <div class="lightbox-caption" :class="{ 'typing-cursor': cancelTyping }">
          {{ captionText }}
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 8000;
  background: rgba(13, 21, 32, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  cursor: pointer;
}

.lightbox-body {
  max-width: 780px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  cursor: default;
}

.lightbox-body img {
  width: 100%;
  height: auto;
  max-height: 55vh;
  object-fit: contain;
  border: 3px solid var(--vp-c-brand-1);
  box-shadow: 0 0 40px rgba(44, 95, 124, 0.2);
  display: block;
}

.lightbox-caption {
  background: #1a2332;
  border: 2px solid #243044;
  border-top: none;
  padding: 1rem 1.25rem;
  color: #e8e2d8;
  font-size: 0.9rem;
  line-height: 1.8;
  min-height: 3.5rem;
}

.typing-cursor::after {
  content: '\25CC';
  color: var(--vp-c-brand-1);
  animation: cursor-blink 0.7s steps(2) infinite;
  margin-left: 2px;
}

@keyframes cursor-blink {
  50% { opacity: 0; }
}
</style>
