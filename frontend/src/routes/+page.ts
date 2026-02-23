import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const response = await fetch('/issues.json');

	if (!response.ok) {
		console.error('Failed to fetch issues:', response.status, response.statusText);
		return { issueMap: {} as Record<string, any> };
	}

	const issues = await response.json();

	if (!Array.isArray(issues)) {
		console.error('Issues response is not an array:', issues);
		return { issueMap: {} as Record<string, any> };
	}

	const issueMap = issues.reduce(
		(acc: Record<string, any>, issue: any) => {
			acc[issue.id] = issue;
			return acc;
		},
		{} as Record<string, any>
	);

	return { issueMap };
};
