using Newtonsoft.Json;

namespace BGGAPI.Src.Entities.Json;

public class BasicJson
{
    [JsonProperty("id")]
    public string Id { get; set; } = null!;
    [JsonProperty("name")]
    public string Name { get; set; } = null!;
    [JsonProperty("url")]
    public string Url { get; set; } = null!;
}