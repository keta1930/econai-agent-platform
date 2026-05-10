<script setup lang="ts">
import DefaultTheme from 'vitepress/theme'
import { onMounted, onUnmounted } from 'vue'

const { Layout } = DefaultTheme

let scrollHandler: (() => void) | null = null
let observer: IntersectionObserver | null = null

onMounted(() => {
  const bar = document.createElement('div')
  bar.className = 'scroll-progress'
  document.body.appendChild(bar)

  scrollHandler = () => {
    const scrollTop = window.scrollY
    const docHeight = document.documentElement.scrollHeight - window.innerHeight
    bar.style.width = docHeight > 0 ? `${(scrollTop / docHeight) * 100}%` : '0%'
  }
  window.addEventListener('scroll', scrollHandler, { passive: true })

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible')
          observer?.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.08 },
  )

  function observeSections() {
    document.querySelectorAll('.vp-doc h2, .vp-doc h3, .vp-doc table, .vp-doc .clickable-img, .vp-doc > div > p, .vp-doc .tip, .vp-doc .warning').forEach((el) => {
      if (!el.classList.contains('fade-section')) {
        el.classList.add('fade-section')
        observer?.observe(el)
      }
    })
  }

  observeSections()

  const mutationObs = new MutationObserver(observeSections)
  const vpDoc = document.querySelector('.vp-doc')
  if (vpDoc) {
    mutationObs.observe(vpDoc, { childList: true, subtree: true })
  }
})

onUnmounted(() => {
  if (scrollHandler) window.removeEventListener('scroll', scrollHandler)
  observer?.disconnect()
  document.querySelector('.scroll-progress')?.remove()
})
</script>

<template>
  <Layout />
</template>
