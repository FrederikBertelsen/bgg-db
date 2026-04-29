
using BGGAPI.Src.Entities;
using BGGAPI.Src.Entities.Dtos;

namespace BGGAPI.Src.Extensions;

public static class DtoExtensions
{
    public static CreditDto ToDto(this Credit credit) => new(credit.Name, credit.Role);
    public static ExpansionDto ToDto(this Expansion expansion) => new(expansion.Name, expansion.Url);
    public static ReimplementsDto ToDto(this Reimplements reimplements) => new(reimplements.Name, reimplements.Url);
    public static RankDto ToDto(this Rank rank) => new(rank.Category, rank.Placement);
    public static VersionDto ToDto(this BoardGameVersion version) => new(version.Name, version.YearPublished, version.Url, version.ImageUrl);
    public static ShopOfferDto ToDto(this ShopOffer shopOffer) => new(
        Seller: shopOffer.Seller,
        Country: shopOffer.SellerCountry ?? string.Empty,
        ProductUrl: shopOffer.ProductUrl ?? string.Empty,
        ImageUrl: shopOffer.ImageUrl ?? string.Empty,
        PriceUSD: shopOffer.PriceUSD ?? 0,
        PriceDKK: shopOffer.PriceDKK ?? 0
    );
    public static PlayerCountScoreDto ToDto(this PlayerCountScore playerCountScore) => new(
        PlayerCount: playerCountScore.PlayerCount,
        Score: playerCountScore.Score
    );
    public static RecommendationDto ToDto(this Recommendation recommendation)
    {
        if (recommendation.RecommendedBoardGame == null)
            throw new InvalidOperationException("Recommendation must have a recommended board game to be converted to DTO.");

        return new(
            Score: recommendation.Score,
            BoardGame: recommendation.RecommendedBoardGame.ToCardDto()
        );
    }

    public static BoardGameCardDto ToCardDto(this BoardGame boardGame) => new(
        Id: boardGame.Id,
        Name: boardGame.Name,
        ShortDescription: boardGame.ShortDescription ?? string.Empty,
        YearPublished: boardGame.YearPublished ?? 0,
        AverageRating: boardGame.AverageRating,
        AverageWeight: boardGame.AverageWeight,
        Ranks: boardGame.Ranks.Select(r => r.ToDto()).ToArray(),
        MinPlayers: boardGame.MinPlayers ?? 0,
        MaxPlayers: boardGame.MaxPlayers ?? 0,
        MinPlaytimeMinutes: boardGame.MinPlaytimeMinutes ?? 0,
        MaxPlaytimeMinutes: boardGame.MaxPlaytimeMinutes ?? 0,
        ThumbnailUrl: boardGame.ImageUrl ?? string.Empty
    );
    public static BoardGameDto ToDto(this BoardGame boardGame) => new(
        Id: boardGame.Id,
        Name: boardGame.Name,
        DescriptionHtml: boardGame.DescriptionHtml ?? string.Empty,
        YearPublished: boardGame.YearPublished ?? 0,
        Url: boardGame.Url,
        WebsiteUrl: boardGame.WebsiteUrl,
        ImageUrl: boardGame.ImageUrl ?? string.Empty,
        MinPlayers: boardGame.MinPlayers ?? 0,
        MaxPlayers: boardGame.MaxPlayers ?? 0,
        PlayerCountBestMin: boardGame.PlayerCountBestMin ?? 0,
        PlayerCountBestMax: boardGame.PlayerCountBestMax ?? 0,
        PlayerCountRecommendedMin: boardGame.PlayerCountRecommendedMin ?? 0,
        PlayerCountRecommendedMax: boardGame.PlayerCountRecommendedMax ?? 0,
        MinPlaytimeMinutes: boardGame.MinPlaytimeMinutes ?? 0,
        MaxPlaytimeMinutes: boardGame.MaxPlaytimeMinutes ?? 0,
        MinAge: boardGame.MinAge ?? 0,
        AverageWeight: boardGame.AverageWeight,
        AverageRating: boardGame.AverageRating,
        PlayCountAllTime: boardGame.PlayCount ?? 0,
        PlayCountLastMonth: boardGame.PlayCountLastMonth ?? 0,
        LanguageDependence: boardGame.LanguageDependence ?? string.Empty,
        EstimatedVolumnCm3: boardGame.EstimatedVolumnCm3 ?? 0,
        EstimatedWeightKg: boardGame.EstimatedWeightKg ?? 0,
        InstructionalVideoId: boardGame.InstructionalVideoId,
        SummaryVideoId: boardGame.SummaryVideoId,
        PlaythroughVideoId: boardGame.PlaythroughVideoId,
        FocusVideoId: boardGame.FocusVideoId,
        HowToPlayVideoId: boardGame.HowToPlayVideoId,
        Categories: boardGame.Categories.Select(c => c.Name).ToArray(),
        Mechanics: boardGame.Mechanics.Select(m => m.Name).ToArray(),
        Families: boardGame.Families.Select(f => f.Name).ToArray(),
        Types: boardGame.Types.Select(t => t.Name).ToArray(),
        Credits: boardGame.Credits.Select(c => c.ToDto()).ToArray(),
        Expansions: boardGame.Expansions.Select(e => e.ToDto()).ToArray(),
        Reimplements: boardGame.Reimplements.Select(r => r.ToDto()).ToArray(),
        Ranks: boardGame.Ranks.Select(r => r.ToDto()).ToArray(),
        Versions: boardGame.Versions.Select(v => v.ToDto()).ToArray(),
        ShopOffers: boardGame.ShopOffers.Select(s => s.ToDto()).ToArray(),
        PlayerCountScores: boardGame.PlayerCountScores.Select(p => p.ToDto()).ToArray(),
        Recommendations: boardGame.RecommendationsFromThis.Select(r => r.ToDto()).ToArray(),
        Honors: boardGame.Honors.ToArray(),
        Subdomains: boardGame.Subdomains.ToArray(),
        ScrapedAt: boardGame.UpdatedAt
    );
}