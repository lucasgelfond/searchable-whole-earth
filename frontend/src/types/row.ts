export type Row = {
	id: string;
	parent_issue_id: string;
	page_number: string;
	ocr_result: string;
	embedding: number[];
	created_at: string;
	image_url: string;
};
