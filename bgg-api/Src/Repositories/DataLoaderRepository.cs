using System.Globalization;
using System.Text.RegularExpressions;
using BGGAPI.Src.Entities;
using BGGAPI.Src.Entities.Json;
using BGGAPI.Src.Repositories.Interfaces;
using CsvHelper;
using Newtonsoft.Json;

namespace BGGAPI.Src.Repositories;

public class DataLoaderRepository() : IDataLoaderRepository
{
    public void LoadLatestDatasetAsync()
    {
        var csvFiles = Directory.GetFiles("./data/final/", "final_*.csv");
        var latestFile = csvFiles.OrderByDescending(f => f).FirstOrDefault()
            ?? throw new FileNotFoundException("No dataset file found in ./data/final/");

        using var reader = new StreamReader(latestFile);
        using var csv = new CsvReader(reader, CultureInfo.InvariantCulture);

        var records = new List<BoardGame>();
        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            int id = ParseInt(csv.GetField<string>("id")) ?? throw new Exception("Id field is required and must be an integer");


            BoardGame readBoardgame = new()
            {
                Id = id,
                Name = csv.GetField<string>("name") ?? throw new Exception("Name field is required"),
                AlternativeNames = ParseStringArray(csv.GetField<string>("alternate_names"))
                    .Select(n => new AlternativeName { Name = n, BoardGameId = id })
                    .ToList(),
                ShortDescription = csv.GetField<string>("short_description"),
                DescriptionHtml = csv.GetField<string>("description"),
                YearPublished = ParseInt(csv.GetField<string>("year_published")),
                Url = csv.GetField<string>("url") ?? throw new Exception("Url field is required"),
                WebsiteUrl = csv.GetField<string>("website_url"),
                ThumbnailUrl = csv.GetField<string>("thumbnail_url"),
                ImageUrl = csv.GetField<string>("image_url"),
                MinPlayers = ParseInt(csv.GetField<string>("min_players")),
                MaxPlayers = ParseInt(csv.GetField<string>("max_players")),
                MinPlaytimeMinutes = ParseInt(csv.GetField<string>("min_playtime")),
                MaxPlaytimeMinutes = ParseInt(csv.GetField<string>("max_playtime")),
                MinAge = ParseInt(csv.GetField<string>("min_age")),
                Weight = Parsefloat(csv.GetField<string>("weight_average")) ?? 0,
                WeightVotes = ParseInt(csv.GetField<string>("weight_votes")),
                AverageRating = Parsefloat(csv.GetField<string>("average_rating")) ?? 0,
                BayesAverageRating = Parsefloat(csv.GetField<string>("bayes_average_rating")),
                StddevRating = Parsefloat(csv.GetField<string>("stddev_rating")),
                RatingVotes = ParseInt(csv.GetField<string>("rating_count")),
                GeeklistCount = ParseInt(csv.GetField<string>("geeklist_count")),
                TradingCount = ParseInt(csv.GetField<string>("trading_count")),
                WantingCount = ParseInt(csv.GetField<string>("wanting_count")),
                WishCount = ParseInt(csv.GetField<string>("wish_count")),
                OwnedCount = ParseInt(csv.GetField<string>("owned_count")),
                PrevOwnedCount = ParseInt(csv.GetField<string>("prev_owned_count")),
                CommentCount = ParseInt(csv.GetField<string>("comment_count")),
                WishlistCommentCount = ParseInt(csv.GetField<string>("wishlist_comment_count")),
                HasPartsCount = ParseInt(csv.GetField<string>("has_parts_count")),
                WantPartsCount = ParseInt(csv.GetField<string>("want_parts_count")),
                PreorderCount = ParseInt(csv.GetField<string>("preorder_count")),
                WantToPlayCount = ParseInt(csv.GetField<string>("want_to_play_count")),
                WantToBuyCount = ParseInt(csv.GetField<string>("want_to_buy_count")),
                ViewCount = ParseInt(csv.GetField<string>("view_count")),
                PlayCount = ParseInt(csv.GetField<string>("play_count")),
                PlayCountLastMonth = ParseInt(csv.GetField<string>("play_count_last_month")),
                FanCount = ParseInt(csv.GetField<string>("fan_count")),
                LanguageDependence = csv.GetField<string>("language_dependence"),
                EstimatedVolumnCm3 = Parsefloat(csv.GetField<string>("estimated_volume_cm3")),
                EstimatedWeightKg = Parsefloat(csv.GetField<string>("estimated_weight_kg")),
                InstructionalVideoId = ParseInt(csv.GetField<string>("instructional_video_id")),
                SummaryVideoId = ParseInt(csv.GetField<string>("summary_video_id")),
                PlaythroughVideoId = ParseInt(csv.GetField<string>("playthrough_video_id")),
                FocusVideoId = ParseInt(csv.GetField<string>("focus_video_id")),
                HowToPlayVideoId = ParseInt(csv.GetField<string>("howtoplay_video_id")),
                Categories = ParseStringArray(csv.GetField<string>("categories"))
                    .Select(c => new Category { Name = c })
                    .ToList(),
                Mechanics = ParseStringArray(csv.GetField<string>("mechanics"))
                    .Select(m => new Mechanic { Name = m })
                    .ToList(),
                Families = ParseStringArray(csv.GetField<string>("families"))
                    .Select(f => new Family { Name = f })
                    .ToList(),
                Types = ParseStringArray(csv.GetField<string>("types"))
                    .Select(t => new BoardGameType { Name = t })
                    .ToList(),
                Credits = ParseCredits(csv.GetField<string>("credits"), id),
                Expansions = ParseExpansions(csv.GetField<string>("expansions"), id),
                Reimplements = ParseReimplements(csv.GetField<string>("reimplementation"), id),
                Ranks = ParseRanks(csv.GetField<string>("ranks"), id),
                Versions = ParseVersions(csv.GetField<string>("versions"), id),
                ShopOffers = ParseShopOffers(csv.GetField<string>("shopping"), id),
                PlayerCountScores = ParsePlayerCountScores(csv.GetField<string>("player_count_scores"), id),
                // skip recommendations as they will be loaded later
                Honors = ParseStringArray(csv.GetField<string>("honors")),
                Subdomains = ParseStringArray(csv.GetField<string>("subdomains"))
            };

            Console.WriteLine(readBoardgame.ToString());

            return;
        }
    }


    private static List<(int, float)> ParsePlayerCountScores(string? input, int boardGameId)
    {
        if (input == null || string.IsNullOrWhiteSpace(input))
            return [];

        var playerCountScores = new List<(int, float)>();

        try
        {
            var playerCountScoreObject = JsonConvert.DeserializeObject(input);

            if (playerCountScoreObject != null)
                if (playerCountScoreObject is Newtonsoft.Json.Linq.JObject playerCountScoreDict)
                    foreach (var kvp in playerCountScoreDict)
                        playerCountScores.Add((
                            int.Parse(kvp.Key),
                            kvp.Value!.ToObject<float>()
                        ));

            return playerCountScores;

        }
        catch (JsonException ex)
        {
            Console.WriteLine($"Failed to parse player count scores JSON: {ex.Message}");
        }

        return playerCountScores;
    }

    private static List<ShopOffer> ParseShopOffers(string? input, int boardGameId)
    {
        if (input == null || string.IsNullOrWhiteSpace(input))
            return [];

        var shopOffers = new List<ShopOffer>();

        try
        {
            var shopOfferObjects = JsonConvert.DeserializeObject<List<ShopOfferJson>>(input);
            if (shopOfferObjects != null)
                foreach (var shopOfferObject in shopOfferObjects)
                    shopOffers.Add(new ShopOffer
                    {
                        Seller = shopOfferObject.Seller,
                        SellerCountry = shopOfferObject.SellerCountry,
                        Currency = shopOfferObject.Currency,
                        Price = float.Parse(shopOfferObject.Price),
                        PriceUSD = float.Parse(shopOfferObject.PriceUsd),
                        PriceDKK = float.Parse(shopOfferObject.PriceDkk),
                        ProductUrl = shopOfferObject.ProductUrl,
                        ImageUrl = shopOfferObject.ImageUrl,
                        BoardGameId = boardGameId
                    });
        }
        catch (JsonException ex)
        {
            Console.WriteLine($"Failed to parse shop offers JSON: {ex.Message}");
        }

        return shopOffers;
    }

    private static List<BoardGameVersion> ParseVersions(string? input, int boardGameId)
    {
        if (input == null || string.IsNullOrWhiteSpace(input))
            return [];

        // Replace unquoted None/NaN with null, then convert single-quoted strings to double quotes
        var sanitized = input.Replace(": None", ": null");

        var versions = new List<BoardGameVersion>();

        try
        {
            var versionObjects = JsonConvert.DeserializeObject<List<VersionJson>>(sanitized);
            if (versionObjects != null)
                foreach (var versionObject in versionObjects)
                {
                    versions.Add(new BoardGameVersion
                    {
                        Name = versionObject.Name,
                        YearPublished = int.Parse(versionObject.YearPublished),
                        WeightKg = float.Parse(versionObject.WeightKg),
                        Width = float.Parse(versionObject.Width),
                        Depth = float.Parse(versionObject.Depth),
                        Length = float.Parse(versionObject.Length),
                        Url = versionObject.Url,
                        ImageUrl = versionObject.ImageUrl,
                        BoardGameId = boardGameId
                    });
                }
        }
        catch (JsonException ex)
        {
            Console.WriteLine($"Failed to parse versions JSON: {ex.Message}");
        }

        return versions;
    }

    private static List<Rank> ParseRanks(string? input, int boardGameId)
    {
        if (input == null || string.IsNullOrWhiteSpace(input))
            return [];

        var ranks = new List<Rank>();

        try
        {
            var rankObjects = JsonConvert.DeserializeObject<List<RankJson>>(input);
            if (rankObjects != null)
                foreach (var rankObject in rankObjects)
                    ranks.Add(new Rank
                    {
                        Category = rankObject.Category,
                        Placement = int.Parse(rankObject.Placement),
                        BayesAverage = float.Parse(rankObject.BayesAverage),
                        BoardGameId = boardGameId
                    });
        }
        catch (JsonException ex)
        {
            Console.WriteLine($"Failed to parse ranks JSON: {ex.Message}");
        }

        return ranks;
    }

    private static List<Reimplements> ParseReimplements(string? input, int boardGameId)
    {
        if (input == null || string.IsNullOrWhiteSpace(input))
            return [];

        var reimplements = new List<Reimplements>();

        try
        {
            var reimplementObjects = JsonConvert.DeserializeObject<List<BasicJson>>(input);
            if (reimplementObjects != null)
                foreach (var reimplementObject in reimplementObjects)
                    reimplements.Add(new Reimplements
                    {
                        Id = int.Parse(reimplementObject.Id),
                        Name = reimplementObject.Name,
                        Url = reimplementObject.Url,
                        BoardGameId = boardGameId
                    });
        }
        catch (JsonException ex)
        {
            Console.WriteLine($"Failed to parse reimplements JSON: {ex.Message}");
        }

        return reimplements;
    }

    private static List<Expansion> ParseExpansions(string? input, int boardGameId)
    {
        if (input == null || string.IsNullOrWhiteSpace(input))
            return [];

        var expansions = new List<Expansion>();

        try
        {
            var expansionObjects = JsonConvert.DeserializeObject<List<BasicJson>>(input);
            if (expansionObjects != null)
                foreach (var expansionObject in expansionObjects)
                    expansions.Add(new Expansion
                    {
                        Id = int.Parse(expansionObject.Id),
                        Name = expansionObject.Name,
                        Url = expansionObject.Url,
                        BoardGameId = boardGameId
                    });
        }
        catch (JsonException ex)
        {
            Console.WriteLine($"Failed to parse expansions JSON: {ex.Message}");
        }

        return expansions;
    }

    private static List<Credit> ParseCredits(string? input, int boardGameId)
    {
        if (input == null || string.IsNullOrWhiteSpace(input))
            return [];

        var credits = new List<Credit>();

        try
        {
            var creditObjects = JsonConvert.DeserializeObject<List<CreditJson>>(input);
            if (creditObjects != null)
                foreach (var creditObject in creditObjects)
                    foreach (var name in creditObject.Names)
                        credits.Add(new Credit
                        {
                            Role = creditObject.Role,
                            Name = name,
                            BoardGameId = boardGameId
                        });
        }
        catch (JsonException ex)
        {
            Console.WriteLine($"Failed to parse credits JSON: {ex.Message}");
        }

        return credits;
    }



    private static string[] ParseStringArray(string? input)
    {
        if (input == null || string.IsNullOrWhiteSpace(input))
            return [];

        var parts = input.Trim('[', ']', '\'').Split("', '").Select(p => p.Trim()).ToArray();

        return parts;
    }

    private static int? ParseInt(string? input)
    {
        if (input == null || string.IsNullOrWhiteSpace(input))
            return null;

        if (int.TryParse(input, out var result))
            return result;

        return null;
    }

    private static float? Parsefloat(string? input)
    {
        if (input == null || string.IsNullOrWhiteSpace(input))
            return null;

        if (float.TryParse(input, NumberStyles.Any, CultureInfo.InvariantCulture, out var result))
            return result;

        return null;
    }
}