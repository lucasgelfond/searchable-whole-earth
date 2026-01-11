import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { getEnv } from "../context";

const PRESIGNED_URL_EXPIRY = 3600; // 1 hour

export async function getPresignedUrl(objectId: string): Promise<string> {
	const env = getEnv();

	const s3 = new S3Client({
		region: "auto",
		endpoint: `https://${env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
		credentials: {
			accessKeyId: env.R2_ACCESS_KEY_ID,
			secretAccessKey: env.R2_SECRET_ACCESS_KEY,
		},
	});

	const command = new GetObjectCommand({
		Bucket: env.R2_BUCKET_NAME,
		Key: objectId,
	});
	return getSignedUrl(s3, command, { expiresIn: PRESIGNED_URL_EXPIRY });
}
