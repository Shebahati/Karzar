/** Lazy-load mock API so production live builds do not bundle mock credentials/PIN. */

export type MockApi = typeof import("./mock-api").mockApi;

export async function getMockApi(): Promise<MockApi> {
  const { mockApi } = await import("./mock-api");
  return mockApi;
}
