import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/tasks',
    },
    {
      path: '/tasks',
      name: 'Tasks',
      component: () => import('@/views/TasksView.vue'),
    },
    {
      path: '/tasks/:id',
      name: 'TaskDetail',
      component: () => import('@/views/TaskDetailView.vue'),
      props: true,
    },
    {
      path: '/annotations',
      name: 'Annotations',
      component: () => import('@/views/AnnotationsView.vue'),
    },
    {
      path: '/tags',
      name: 'Tags',
      component: () => import('@/views/TagsView.vue'),
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/SettingsView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

export default router
