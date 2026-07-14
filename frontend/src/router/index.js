import { createRouter, createWebHistory } from 'vue-router'

import GuestHomePage from '@/views/GuestHomePage.vue'
import LoginPage from '@/views/LoginPage.vue'
import RegisterPage from '@/views/RegisterPage.vue'

import AppShell from '@/layout/AppShell.vue'
import ChatPage from '@/views/ChatPage.vue'
import DetectionPage from '@/views/DetectionPage.vue'
import TrainingPage from '@/views/TrainingPage.vue'
import ModelsPage from '@/views/ModelsPage.vue'

const routes = [
  {
    path: '/',
    name: 'GuestHome',
    component: GuestHomePage,
    meta: {
      public: true,
      guestOnly: true,
    },
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginPage,
    meta: {
      public: true,
      guestOnly: true,
    },
  },
  {
    path: '/register',
    name: 'Register',
    component: RegisterPage,
    meta: {
      public: true,
      guestOnly: true,
    },
  },
  {
    path: '/',
    component: AppShell,
    redirect: '/chat',
    children: [
      {
        path: 'chat',
        name: 'Chat',
        component: ChatPage,
        meta: {
          roles: ['user', 'developer', 'admin'],
        },
      },
      {
        path: 'detection',
        name: 'Detection',
        component: DetectionPage,
        meta: {
          roles: ['user', 'developer', 'admin'],
        },
      },
      {
        path: 'training',
        name: 'Training',
        component: TrainingPage,
        meta: {
          roles: ['developer', 'admin'],
        },
      },
      {
        path: 'models',
        name: 'Models',
        component: ModelsPage,
        meta: {
          roles: ['developer', 'admin'],
        },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token =
    localStorage.getItem('access_token') ||
    localStorage.getItem('token')

  const role =
    localStorage.getItem('user_role') ||
    localStorage.getItem('role') ||
    'user'

  if (to.meta.public) {
    if (to.meta.guestOnly && token) {
      return next('/chat')
    }

    return next()
  }

  if (!token) {
    return next('/login')
  }

  if (to.meta.roles && !to.meta.roles.includes(role)) {
    return next('/chat')
  }

  next()
})

export default router