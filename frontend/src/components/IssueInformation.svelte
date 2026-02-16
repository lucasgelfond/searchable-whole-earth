<script lang="ts">
export let issue: any;
export let collectionMap: Record<string, string>;
export let currentPageNumber: number;
</script>

<div class="flex flex-col gap-3">
  <div class="text-2xl font-bold text-white">{collectionMap[issue.collection]}</div>
  <div class="text-white/90 text-sm italic">{@html issue.description}</div>
  <div class="flex gap-4 text-sm">
    <a
      href={issue.internet_archive}
      class="text-white hover:underline"
      target="_blank"
      on:click|stopPropagation
    >
      Archive
    </a>
    <a
      href={issue.issue_url}
      class="text-white hover:underline"
      target="_blank"
      on:click|stopPropagation
    >
      Info
    </a>
    <a
      href={issue.pdf_download}
      class="text-white hover:underline"
      target="_blank"
      on:click|stopPropagation
    >
      PDF
    </a>
  </div>
  <div class="flex flex-col text-sm text-white/80">
    <div>Published: {issue.pub_date}</div>
    <div>Page {currentPageNumber}/{issue.num_pages}</div>
  </div>
</div>