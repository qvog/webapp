import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'
import './style.css'
import App from './App.vue'

const app = createApp(App)

app.use(createPinia())
app.use(Toast, {
  position: "top-right",
  transition: "Vue-Toastification__fade", 
  timeout: 2000,
  closeOnClick: true,
  pauseOnFocusLoss: false,
  pauseOnHover: true,
  draggable: false,
  hideProgressBar: true,
  icon: false,
  toastClassName: "hft-compact-toast",
})

app.mount('#app')