<script lang="ts">
import { page } from '$app/stores';
</script>

<div class="flex flex-col items-center justify-center h-screen bg-white dark:bg-black text-black dark:text-white px-4">
  <h1 class="text-4xl font-bold">{$page.status}</h1>
  <p class="mt-4 text-lg text-gray-600 dark:text-gray-400">{$page.error?.message}</p>
  <a href="/" class="mt-6 underline hover:opacity-70">Back to search</a>
</div>
