import { createRouter, createWebHistory } from 'vue-router'
import { ChatView } from '@/features/chat'
import { WorkspaceView, WorkspaceDetailView } from '@/features/workspaces'
import { PapersImportView } from '@/features/papers'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Chat',
      component: ChatView
    },
    {
      path: '/workspaces',
      name: 'Workspaces',
      component: WorkspaceView
    },
    {
      path: '/workspace/:id',
      name: 'WorkspaceDetail',
      component: WorkspaceDetailView,
      props: true
    },
    {
      path: '/papers',
      name: 'PapersImport',
      component: PapersImportView
    },
    {
      path: '/workspace/:id/papers',
      name: 'WorkspacePapersImport',
      component: PapersImportView,
      props: route => ({ workspaceId: route.params.id })
    }
  ]
})

export default router