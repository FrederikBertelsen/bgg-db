using Newtonsoft.Json;

namespace BGGAPI.Src.Entities.Json;

public class ShopOfferJson
{
    [JsonProperty("seller")]
    public string Seller { get; set; } = null!;
    [JsonProperty("seller_country")]
    public string SellerCountry { get; set; } = null!;
    [JsonProperty("currency")]
    public string Currency { get; set; } = null!;
    [JsonProperty("price")]
    public string Price { get; set; } = null!;
    [JsonProperty("product_url")]
    public string ProductUrl { get; set; } = null!;
    [JsonProperty("image_url")]
    public string ImageUrl { get; set; } = null!;
    [JsonProperty("price_usd")]
    public string PriceUsd { get; set; } = null!;
    [JsonProperty("price_dkk")]
    public string PriceDkk { get; set; } = null!;
}


// {
//     "seller":"Dryad Games",
//     "seller_country":"US",
//     "currency":"USD",
//     "price":"99.99",
//     "product_url":"https:\/\/dryad-games.com\/shop\/galactic-cruise\/aff\/2\/",
//     "image_url":"https:\/\/cf.geekdo-images.com\/Kc6Ru44-wTMNCvjp5P0HJw__affiliatelogo\/img\/5O6SV_cemmthdd_BufQQyHQpraM=\/fit-in\/0x22\/filters:strip_icc()\/pic8575752.jpg",
//     "price_usd":99.99,
//     "price_dkk":637.94
// },