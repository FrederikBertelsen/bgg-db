using Newtonsoft.Json;

namespace BGGAPI.Src.Entities.Json;

public class RankJson
{
    [JsonProperty("category")]
    public string Category { get; set; } = null!;
    [JsonProperty("rank")]
    public string Placement { get; set; } = null!;
    [JsonProperty("bayes_average")]
    public string BayesAverage { get; set; } = null!;
}