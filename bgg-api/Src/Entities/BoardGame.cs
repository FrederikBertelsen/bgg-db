using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

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

    public double AverageWeight { get; set; }
    public int? WeightVotes { get; set; }

    public double AverageRating { get; set; }
    public double? BayesAverageRating { get; set; }
    public double? StddevRating { get; set; }
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

    public decimal? EstimatedVolumnCm3 { get; set; }
    public decimal? EstimatedWeightKg { get; set; }

    public int? InstructionalVideoId { get; set; }
    public int? SummaryVideoId { get; set; }
    public int? PlaythroughVideoId { get; set; }
    public int? FocusVideoId { get; set; }
    public int? HowToPlayVideoId { get; set; }

    public ICollection<Category> Categories { get; set; } = new HashSet<Category>();
    public ICollection<Mechanic> Mechanics { get; set; } = new HashSet<Mechanic>();
    public ICollection<Family> Families { get; set; } = new HashSet<Family>();
    public ICollection<BoardGameType> Types { get; } = new HashSet<BoardGameType>();

    public ICollection<Credit> Credits { get; set; } = new List<Credit>();
    public ICollection<Expansion> Expansions { get; set; } = new List<Expansion>();
    public ICollection<Reimplements> Reimplements { get; set; } = new List<Reimplements>();

    public ICollection<Rank> Ranks { get; set; } = new List<Rank>();
    public ICollection<BoardGameVersion> Versions { get; } = new List<BoardGameVersion>();
    public ICollection<ShopOffer> ShopOffers { get; } = new List<ShopOffer>();
    public ICollection<PlayerCountScore> PlayerCountScores { get; set; } = new List<PlayerCountScore>();

    public ICollection<Recommendation> RecommendationsFromThis { get; } = new List<Recommendation>();
    public ICollection<Recommendation> RecommendationsToThis { get; } = new List<Recommendation>();

    [NotMapped]
    public ICollection<string> Honors { get; set; } = new List<string>();

    [NotMapped]
    public ICollection<string> Subdomains { get; set; } = new List<string>();

    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}