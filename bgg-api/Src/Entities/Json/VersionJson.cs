using Newtonsoft.Json;

namespace BGGAPI.Src.Entities.Json;

public class VersionJson
{
    [JsonProperty("name")]
    public string Name { get; set; } = null!;
    [JsonProperty("year_published")]
    public string YearPublished { get; set; } = null!;
    [JsonProperty("weight_kg")]
    public string WeightKg { get; set; } = null!;
    [JsonProperty("width")]
    public string Width { get; set; } = null!;
    [JsonProperty("depth")]
    public string Depth { get; set; } = null!;
    [JsonProperty("length")]
    public string Length { get; set; } = null!;
    [JsonProperty("url")]
    public string Url { get; set; } = null!;
    [JsonProperty("image_url")]
    public string? ImageUrl { get; set; } = null!;
}