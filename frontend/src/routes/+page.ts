import type { PageLoad } from './$types';
import type { Issue, IssueMap } from '../utils/api';

export const load: PageLoad = async ({ fetch }) => {
	const response = await fetch('/issues.json');

	if (!response.ok) {
		console.error('Failed to fetch issues:', response.status, response.statusText);
		return { issueMap: {} as IssueMap };
	}

	const issues = await response.json();

	if (!Array.isArray(issues)) {
		console.error('Issues response is not an array:', issues);
		return { issueMap: {} as IssueMap };
	}

	const issueMap = issues.reduce(
		(acc: IssueMap, issue: Issue) => {
			acc[issue.id] = issue;
			return acc;
		},
		{} as IssueMap
	);

	return { issueMap };
};
