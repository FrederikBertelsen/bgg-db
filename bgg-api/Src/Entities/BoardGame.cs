using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using System.Text;

namespace BGGAPI.Src.Entities;

public class BoardGame
{
    [Key]
    [DatabaseGenerated(DatabaseGeneratedOption.None)]
    public required int Id { get; set; }

    public required string Name { get; set; }
    public ICollection<AlternativeName> AlternativeNames { get; set; } = new HashSet<AlternativeName>();

    public string? ShortDescription { get; set; }
    public string? DescriptionHtml { get; set; }

    public int? YearPublished { get; set; }

    public required string Url { get; set; }
    public string? WebsiteUrl { get; set; }
    public string? ThumbnailUrl { get; set; }
    public string? ImageUrl { get; set; }

    public int? MinPlayers { get; set; }
    public int? MaxPlayers { get; set; }

    public int? PlayerCountBestMin { get; set; }
    public int? PlayerCountBestMax { get; set; }
    public int? PlayerCountRecommendedMin { get; set; }
    public int? PlayerCountRecommendedMax { get; set; }
    public int? PlayerCountVotes { get; set; }

    public int? MinPlaytimeMinutes { get; set; }
    public int? MaxPlaytimeMinutes { get; set; }
    public int? MinAge { get; set; }

    public float Weight { get; set; }
    public int? WeightVotes { get; set; }

    public float AverageRating { get; set; }
    public float? BayesAverageRating { get; set; }
    public float? StddevRating { get; set; }
    public int? RatingVotes { get; set; }

    public int? GeeklistCount { get; set; }
    public int? TradingCount { get; set; }
    public int? WantingCount { get; set; }
    public int? WishCount { get; set; }
    public int? OwnedCount { get; set; }
    public int? PrevOwnedCount { get; set; }
    public int? CommentCount { get; set; }
    public int? WishlistCommentCount { get; set; }
    public int? HasPartsCount { get; set; }
    public int? WantPartsCount { get; set; }
    public int? PreorderCount { get; set; }
    public int? WantToPlayCount { get; set; }
    public int? WantToBuyCount { get; set; }
    public int? ViewCount { get; set; }
    public int? PlayCount { get; set; }
    public int? PlayCountLastMonth { get; set; }
    public int? FanCount { get; set; }

    public string? LanguageDependence { get; set; }

    public float? EstimatedVolumnCm3 { get; set; }
    public float? EstimatedWeightKg { get; set; }

    public int? InstructionalVideoId { get; set; }
    public int? SummaryVideoId { get; set; }
    public int? PlaythroughVideoId { get; set; }
    public int? FocusVideoId { get; set; }
    public int? HowToPlayVideoId { get; set; }

    public ICollection<Category> Categories { get; set; } = new HashSet<Category>();
    public ICollection<Mechanic> Mechanics { get; set; } = new HashSet<Mechanic>();
    public ICollection<Family> Families { get; set; } = new HashSet<Family>();
    public ICollection<BoardGameType> Types { get; set; } = new HashSet<BoardGameType>();

    public ICollection<Credit> Credits { get; set; } = new List<Credit>();
    public ICollection<Expansion> Expansions { get; set; } = new List<Expansion>();
    public ICollection<Reimplements> Reimplements { get; set; } = new List<Reimplements>();

    public ICollection<Rank> Ranks { get; set; } = new List<Rank>();
    public ICollection<BoardGameVersion> Versions { get; set; } = new List<BoardGameVersion>();
    public ICollection<ShopOffer> ShopOffers { get; set; } = new List<ShopOffer>();
    [NotMapped]
    public ICollection<(int, float)> PlayerCountScores { get; set; } = new List<(int, float)>();

    public ICollection<Recommendation> RecommendationsFromThis { get; } = new List<Recommendation>();
    public ICollection<Recommendation> RecommendationsToThis { get; } = new List<Recommendation>();

    [NotMapped]
    public ICollection<string> Honors { get; set; } = new List<string>();

    [NotMapped]
    public ICollection<string> Subdomains { get; set; } = new List<string>();

    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;


    public override string ToString()
    {
        var sBuilder = new StringBuilder();
        sBuilder.AppendLine($"Name: {Name}");
        sBuilder.AppendLine($"  Url: {Url}");
        sBuilder.AppendLine($"  Year Published: {YearPublished}");
        sBuilder.AppendLine($"  Average Rating: {AverageRating}");
        sBuilder.AppendLine($"  Bayes Average Rating: {BayesAverageRating}");
        sBuilder.AppendLine($"  Rating Votes: {RatingVotes}");
        sBuilder.AppendLine($"  Min Players: {MinPlayers}");
        sBuilder.AppendLine($"  Max Players: {MaxPlayers}");
        sBuilder.AppendLine($"  Min Playtime: {MinPlaytimeMinutes}");
        sBuilder.AppendLine($"  Max Playtime: {MaxPlaytimeMinutes}");
        sBuilder.AppendLine($"  Min Age: {MinAge}");
        sBuilder.AppendLine($"  Language Dependence: {LanguageDependence}");
        sBuilder.AppendLine($"  Estimated Volume (cm3): {EstimatedVolumnCm3}");
        sBuilder.AppendLine($"  Estimated Weight (kg): {EstimatedWeightKg}");
        sBuilder.AppendLine($"  Fan Count: {FanCount}");
        sBuilder.AppendLine($"  Average Weight: {Weight}");
        sBuilder.AppendLine($"  Weight Votes: {WeightVotes}");
        sBuilder.AppendLine($"  Stddev Rating: {StddevRating}");
        sBuilder.AppendLine($"  Categories:\n      {string.Join("\n      ", Categories.Select(c => c.Name))}");
        sBuilder.AppendLine($"  Mechanics:\n      {string.Join("\n      ", Mechanics.Select(m => m.Name))}");
        sBuilder.AppendLine($"  Families:\n      {string.Join("\n      ", Families.Select(f => f.Name))}");
        sBuilder.AppendLine($"  Types:\n      {string.Join("\n      ", Types.Select(t => t.Name))}");
        sBuilder.AppendLine($"  Honors:\n      {string.Join("\n      ", Honors)}");
        sBuilder.AppendLine($"  Subdomains:\n      {string.Join("\n      ", Subdomains)}");
        sBuilder.AppendLine($"  ThumbnailUrl: {ThumbnailUrl}");
        sBuilder.AppendLine($"  ImageUrl: {ImageUrl}");
        sBuilder.AppendLine($"  WebsiteUrl: {WebsiteUrl}");
        sBuilder.AppendLine($"  Description: {ShortDescription}");
        sBuilder.AppendLine($"  Description HTML: {DescriptionHtml}");
        sBuilder.AppendLine($"  Player Count Scores:\n      {string.Join("\n      ", PlayerCountScores.Select(p => $"{p.Item1}: {p.Item2}"))}");
        sBuilder.AppendLine($"  Credits:\n      {string.Join("\n      ", Credits.Select(c => $"{c.Name} ({c.Role})"))}");
        sBuilder.AppendLine($"  Expansions:\n      {string.Join("\n      ", Expansions.Select(e => $"{e.Name} ({e.Url})"))}");
        sBuilder.AppendLine($"  Reimplements:\n      {string.Join("\n      ", Reimplements.Select(r => $"{r.Name} ({r.Url})"))}");
        sBuilder.AppendLine($"  Ranks:\n      {string.Join("\n      ", Ranks.Select(r => $"{r.Category}: {r.Placement} ({r.BayesAverage})"))}");
        sBuilder.AppendLine($"  Versions:\n      {string.Join("\n      ", Versions.Select(v => $"{v.Name} ({v.YearPublished}) - {v.Url})"))}");
        sBuilder.AppendLine($"  Shop Offers:\n      {string.Join("\n      ", ShopOffers.Select(s => $"{s.Seller}: {s.Price} ({s.ProductUrl})"))}");
        sBuilder.AppendLine($"  Alternative Names:\n      {string.Join("\n      ", AlternativeNames.Select(a => a.Name))}");
        sBuilder.AppendLine($"  Recommendations From This:\n      {string.Join("\n      ", RecommendationsFromThis.Select(r => r.RecommendedBoardGame!.Name))}");
        sBuilder.AppendLine($"  Recommendations To This:\n      {string.Join("\n      ", RecommendationsToThis.Select(r => r.SeedBoardGame!.Name))}");
        sBuilder.AppendLine($"  Created At: {CreatedAt}");
        sBuilder.AppendLine($"  Updated At: {UpdatedAt}");
        return sBuilder.ToString();
    }
}