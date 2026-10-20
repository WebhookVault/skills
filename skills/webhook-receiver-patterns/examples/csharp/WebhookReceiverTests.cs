// Drives the receiver through ASP.NET Core's in-memory test server. Signatures are made with the
// openssl command line, not with the code under test.

using System.Diagnostics;
using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace WebhookReceiver;

public sealed class WebhookReceiverTests : IAsyncLifetime
{
    private const string Secret = "test-receiver-secret";
    private const long Now = 1760000000;

    private sealed class RecordingQueue : IEventQueue
    {
        public List<string> Ids { get; } = [];
        public bool FailNext { get; set; }
        public Task EnqueueAsync(JsonElement evt, CancellationToken ct)
        {
            if (FailNext) { FailNext = false; throw new InvalidOperationException("queue down"); }
            Ids.Add(evt.GetProperty("id").GetString()!);
            return Task.CompletedTask;
        }
    }

    private readonly RecordingQueue _queue = new();
    private WebApplication _app = null!;
    private HttpClient _client = null!;

    public async Task InitializeAsync()
    {
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        builder.Services.AddSingleton<IEventStore, MemoryEventStore>();
        builder.Services.AddSingleton<IEventQueue>(_queue);
        _app = builder.Build();
        _app.MapWebhooks(new ReceiverOptions(Secret, () => Now));
        await _app.StartAsync();
        _client = _app.GetTestClient();
    }

    public async Task DisposeAsync() => await _app.DisposeAsync();

    /// <summary>The openssl command line: OPENSSL if set, else openssl on PATH (Git Bash on Windows has it).</summary>
    private static readonly string Openssl = Environment.GetEnvironmentVariable("OPENSSL") is { Length: > 0 } path ? path : "openssl";

    private static string OpensslSign(long t, byte[] body)
    {
        var psi = new ProcessStartInfo(Openssl, $"dgst -sha256 -hmac {Secret} -hex")
        {
            RedirectStandardInput = true, RedirectStandardOutput = true, UseShellExecute = false,
        };
        Process p;
        try { p = Process.Start(psi)!; }
        catch (System.ComponentModel.Win32Exception)
        {
            throw new InvalidOperationException("These tests sign requests with the openssl command line: put openssl 3 on PATH or set OPENSSL to its path (run them from Git Bash on Windows).");
        }
        using var _ = p;
        p.StandardInput.BaseStream.Write([.. Encoding.UTF8.GetBytes($"{t}."), .. body]);
        p.StandardInput.Close();
        var output = p.StandardOutput.ReadToEnd();
        p.WaitForExit();
        return output.Trim().Split(' ').Last();
    }

    private Task<HttpResponseMessage> Post(string body, long t = Now, string? signature = null, bool withSignature = true)
    {
        var bytes = Encoding.UTF8.GetBytes(body);
        var request = new HttpRequestMessage(HttpMethod.Post, "/webhooks") { Content = new ByteArrayContent(bytes) };
        request.Content.Headers.ContentType = new("application/json");
        if (withSignature) request.Headers.Add("Webhook-Signature", signature ?? $"t={t},v1={OpensslSign(t, bytes)}");
        return _client.SendAsync(request);
    }

    [Fact]
    public async Task a_signed_event_is_acknowledged_and_queued_once()
    {
        var res = await Post("""{"id":"evt_test_a","type":"order.created"}""");
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
        Assert.Equal(["evt_test_a"], _queue.Ids);
    }

    [Fact]
    public async Task the_same_event_again_is_acknowledged_and_not_queued_twice()
    {
        await Post("""{"id":"evt_test_b"}""");
        var res = await Post("""{"id":"evt_test_b"}""");
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
        Assert.Contains("\"duplicate\":true", await res.Content.ReadAsStringAsync());
        Assert.Equal(["evt_test_b"], _queue.Ids);
    }

    [Fact]
    public async Task a_wrong_signature_is_refused_and_nothing_is_queued()
    {
        var res = await Post("""{"id":"evt_test_c"}""", signature: $"t={Now},v1={new string('0', 64)}");
        Assert.Equal(HttpStatusCode.Unauthorized, res.StatusCode);
        Assert.Empty(_queue.Ids);
    }

    [Fact]
    public async Task an_unverified_request_does_not_use_up_the_event_id()
    {
        await Post("""{"id":"evt_test_d"}""", signature: "t=1,v1=bad");
        var res = await Post("""{"id":"evt_test_d"}""");
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
        Assert.Equal(["evt_test_d"], _queue.Ids);
    }

    [Fact]
    public async Task a_stale_timestamp_is_refused() => Assert.Equal(HttpStatusCode.Unauthorized, (await Post("""{"id":"evt_test_e"}""", t: Now - 3600)).StatusCode);

    [Fact]
    public async Task a_missing_signature_header_is_refused() => Assert.Equal(HttpStatusCode.Unauthorized, (await Post("""{"id":"evt_test_f"}""", withSignature: false)).StatusCode);

    [Fact]
    public async Task a_signed_body_that_is_not_json_is_refused_with_400() => Assert.Equal(HttpStatusCode.BadRequest, (await Post("not json")).StatusCode);

    [Fact]
    public async Task a_signed_event_without_an_id_is_refused() => Assert.Equal(HttpStatusCode.BadRequest, (await Post("""{"type":"order.created"}""")).StatusCode);

    [Fact]
    public async Task a_body_over_the_limit_is_refused_with_413()
    {
        var big = "{\"id\":\"evt_test_big\",\"pad\":\"" + new string('x', ReceiverOptions.MaxBodyBytes) + "\"}";
        Assert.Equal(HttpStatusCode.RequestEntityTooLarge, (await Post(big)).StatusCode);
    }

    [Fact]
    public async Task a_failed_hand_off_answers_500()
    {
        _queue.FailNext = true;
        Assert.Equal(HttpStatusCode.InternalServerError, (await Post("""{"id":"evt_test_g"}""")).StatusCode);
    }

    [Fact]
    public async Task the_signature_covers_the_exact_bytes()
    {
        var sig = $"t={Now},v1={OpensslSign(Now, Encoding.UTF8.GetBytes("""{"id":"evt_test_h"}"""))}";
        Assert.Equal(HttpStatusCode.Unauthorized, (await Post("""{ "id": "evt_test_h" }""", signature: sig)).StatusCode);
    }
}
