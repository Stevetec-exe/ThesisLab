import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";

const S3Url = process.env.S3_URL ?? "http://localhost:8333/context";

const url = new URL(S3Url);
const bucket = url.pathname.replace(/^\/|\/$/g, "");

const s3 = new S3Client({
  endpoint: `${url.protocol}//${url.host}`,
  region: process.env.AWS_REGION ?? "us-east-1",
  forcePathStyle: true, // useful for S3-compatible storage such as MinIO
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID ?? "admin",
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY ?? "secret",
  },
});

export async function download(id: string): Promise<Buffer> {
  const response = await s3.send(
    new GetObjectCommand({
      Bucket: bucket,
      Key: id,
    }),
  );

  if (!response.Body) {
    throw new Error(`S3 object "${id}" has no body`);
  }

  return Buffer.from(await response.Body.transformToByteArray());
}