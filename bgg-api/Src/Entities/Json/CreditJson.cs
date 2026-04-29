using Newtonsoft.Json;

namespace BGGAPI.Src.Entities.Json
{
    public class CreditJson
    {
        [JsonProperty("role")]
        public string Role { get; set; } = null!;
        [JsonProperty("names")]
        public string[] Names { get; set; } = [];
    }
}