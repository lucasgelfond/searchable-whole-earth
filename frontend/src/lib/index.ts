import { writable } from 'svelte/store';

export const searchQuery = writable('');

export function highlightQuery(text: string, query: string): string {
	const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
	if (!query.trim()) return escaped;
	const pattern = query.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	return escaped.replace(new RegExp(`(${pattern})`, 'gi'), '<span class="bg-white text-black">$1</span>');
}
