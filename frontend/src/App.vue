<script setup>
import { computed } from 'vue'
import { t } from './i18n'
import SiteHeader from './components/SiteHeader.vue'

const year = computed(() => new Date().getFullYear())
</script>

<template>
  <div class="container">
    <SiteHeader />
    <div id="body">
      <router-view />
    </div>
    <footer id="footer">
      {{ t('title') }} · {{ year }} · {{ t('footnote') }}
    </footer>
  </div>
</template>
