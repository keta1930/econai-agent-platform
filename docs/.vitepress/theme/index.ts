import DefaultTheme from 'vitepress/theme'
import CustomLayout from './CustomLayout.vue'
import ImageViewer from './ImageViewer.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout: CustomLayout,
  enhanceApp({ app }) {
    app.component('ImageViewer', ImageViewer)
  },
}
