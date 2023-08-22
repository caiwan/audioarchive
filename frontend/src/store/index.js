import { createStore, createLogger } from 'vuex'
import UI from './ui'
import App from './app'

const debug = process.env.NODE_ENV !== 'production'

export default createStore({
    modules: {
      UI,
      App,
    },
    strict: debug,
    plugins: debug ? [createLogger()] : []
  })