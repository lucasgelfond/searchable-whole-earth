<script lang="ts">
import SearchResult from './SearchResult.svelte';

let { results = [], issueMap = {}, openModal, query = '' }: {
	results?: any[];
	issueMap?: Record<string, any>;
	openModal: (item: any, issue: any) => void;
	query?: string;
} = $props();

function showResultModal(item: any) {
	const issue = issueMap[item.parent_issue_id];
	openModal(item, issue);
}
</script>

{#if results.length}
  <div class="pt-4">
    <h3 class="font-bold pb-3">{results.length} result{results.length === 1 ? '' : 's'}</h3>
    <div class="grid gap-4">
      {#each results as item}
        <SearchResult
          {item}
          {issueMap}
          {query}
          onselect={showResultModal}
        />
      {/each}
    </div>
  </div>
{/if}
