import Foundation

public actor BackendClient {
    public enum ClientError: Error {
        case invalidURL
        case requestFailed
    }

    public var baseURL: URL

    public init(baseURL: URL = URL(string: ProcessInfo.processInfo.environment["CLONE_BACKEND_URL"] ?? "http://localhost:4000")!) {
        self.baseURL = baseURL
    }

    public func health() async throws -> String {
        let url = baseURL.appending(path: "health")
        let (data, response) = try await URLSession.shared.data(from: url)
        guard
            let httpResponse = response as? HTTPURLResponse,
            httpResponse.statusCode == 200,
            let body = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let status = body["status"] as? String
        else {
            throw ClientError.requestFailed
        }
        return status
    }
}
