import { createWebHistory, createRouter } from "vue-router";

import Home from "@/components/pages/Home.vue";
import Catalog from "@/components/pages/Catalog.vue";

const routes = [
  {
    path: "/",
    name: "Home",
    component: Home,
  },
  {
    path: "/catalog",
    name: "Catlaog",
    component: Catalog,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;