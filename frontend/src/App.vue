<!--
  App.vue — 根组件

  作用：作为整个应用的外壳，包含：
  1. <router-view /> — 路由出口，根据当前 URL 渲染对应的页面组件
  2. 全局 CSS 重置 — 统一浏览器默认样式
-->
<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
// 根组件无需业务逻辑，仅作为路由容器
</script>

<style>
/* 全局 CSS 重置：消除浏览器默认的 margin/padding，统一盒模型 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* 全局字体和背景色 */
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f7fa;
  min-height: 100vh;
}

/* 确保 app 容器至少占满视口高度 */
#app {
  min-height: 100vh;
}
</style>
