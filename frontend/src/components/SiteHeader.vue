<script setup>
import { t, toggleLang, lang } from '../i18n'
</script>

<template>
  <header id="header" class="clearfix">
    <div class="site-name">
      <router-link to="/" class="logo">{{ t('title') }}</router-link>
      <p class="description">{{ t('subtitle') }}</p>
    </div>
    <button class="lang-toggle" @click="toggleLang">{{ t('langToggle') }}</button>
    <nav class="nav" role="navigation">
      <router-link to="/">{{ t('navAnalyze') }}</router-link>
      <router-link to="/history">{{ t('navHistory') }}</router-link>
    </nav>
  </header>
</template>
