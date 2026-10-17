import { createRouter, createWebHashHistory } from 'vue-router'
import AnalyzeView from './views/AnalyzeView.vue'
import HistoryView from './views/HistoryView.vue'

export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: AnalyzeView },
    { path: '/history', component: HistoryView },
  ],
})
