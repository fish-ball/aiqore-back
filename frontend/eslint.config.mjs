import vue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import vueParser from 'vue-eslint-parser'

/** @type {import('eslint').Linter.Config[]} */
const vueRecommended = vue.configs['flat/recommended'] || []

export default [
  // Vue 推荐（Flat Config）。有的版本导出对象，有的版本导出数组，这里统一铺平。
  ...(Array.isArray(vueRecommended) ? vueRecommended : [vueRecommended]),
  // TypeScript 推荐（Flat Config）
  ...tseslint.configs.recommended,
  // 让 ESLint 能正确解析 .vue SFC（<template>/<script>）
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        extraFileExtensions: ['.vue'],
        ecmaVersion: 'latest',
        sourceType: 'module'
      }
    }
  },
  // 项目级收紧规则（先从 warn 开始，避免迁移期阻断）
  {
    files: ['**/*.ts', '**/*.tsx', '**/*.vue'],
    rules: {
      // 迁移期先不强制多词组件名，避免大量存量文件报错
      'vue/multi-word-component-names': 'off',
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }]
    }
  }
]

