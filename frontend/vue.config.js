const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    host: '0.0.0.0',
  },
  runtimeCompiler: true,
  configureWebpack: {
    watchOptions: {
      poll: true,
      aggregateTimeout: 300,
      poll: 500
    }
  }
})
