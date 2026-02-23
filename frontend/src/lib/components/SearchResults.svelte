<script lang="ts">
import type { SearchResult as SearchResultType, Issue, IssueMap } from '../../utils/api';
import SearchResult from './SearchResult.svelte';

let { results = [], issueMap = {}, openModal, query = '' }: {
	results?: SearchResultType[];
	issueMap?: IssueMap;
	openModal: (item: SearchResultType, issue: Issue) => void;
	query?: string;
} = $props();

function showResultModal(item: SearchResultType) {
	if (!item.parent_issue_id) return;
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
